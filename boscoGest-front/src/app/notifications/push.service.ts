import { openNotification } from './notification-navigation';
import { MatSnackBar } from '@angular/material/snack-bar';
import { InjectionToken, Injectable, NgZone, inject } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';
import {
  ActionPerformed,
  PushNotifications,
  PushNotificationSchema,
  PushNotificationsPlugin,
  Token,
} from '@capacitor/push-notifications';
import { environment } from '../../environments/environment';
import { NotificationService } from './notification.service';
import { BACKGROUND_REQUEST } from '../shared/loading/loading';

/**
 * El plugin, inyectado en vez de importado directamente.
 *
 * Capacitor expone los plugins a través de un proxy que devuelve una función
 * nueva en cada acceso, así que `spyOn` no se le pega y el servicio sería
 * imposible de probar sin un dispositivo. Con un token, un test puede
 * sustituirlo por un doble.
 */
export const PUSH_PLUGIN = new InjectionToken<PushNotificationsPlugin>(
  'PUSH_PLUGIN',
  { providedIn: 'root', factory: () => PushNotifications }
);

/** Lo que el servidor mete en `data`. Solo identificadores, nunca datos
 *  personales: el aviso se ve en la pantalla bloqueada. */
interface PushData {
  event_type?: string;
  resource_type?: string;
  resource_id?: string;
}

/**
 * Notificaciones push del sistema operativo.
 *
 * Complementa al WebSocket, que solo entrega mientras la aplicación está
 * abierta. En móvil el WebSocket ni siquiera se usa —lo bloquea la política de
 * contenido mixto y se recurre al sondeo—, así que el push es la única forma
 * de enterarse de algo sin abrir la aplicación.
 *
 * Todo esto es no-op en web: `Capacitor.isNativePlatform()` es false y el
 * plugin no existe fuera de iOS y Android.
 */
@Injectable({ providedIn: 'root' })
export class PushService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private notifications = inject(NotificationService);
  private zone = inject(NgZone);
  private snackBar = inject(MatSnackBar);
  private push = inject(PUSH_PLUGIN);

  private apiUrl = `${environment.apiUrl}/notifications/devices`;
  /** El último token registrado, para poder darlo de baja al cerrar sesión. */
  private token: string | null = null;
  private listenersReady = false;

  /**
   * Pide permiso y registra el dispositivo. Se llama tras iniciar sesión.
   *
   * Es idempotente a propósito: conviene llamarlo en cada arranque, porque el
   * token que emite el sistema caduca y se renueva solo, y si no se vuelve a
   * mandar el servidor se queda apuntando a uno que ya no existe.
   */
  async register(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;
    // Sin google-services.json, el plugin lanza una excepción en Java que el
    // catch de abajo no ve: la aplicación se cerraba al iniciar sesión.
    if (Capacitor.getPlatform() === 'android' && !environment.androidPush) {
      console.warn('Push desactivado en Android: la compilación no lleva google-services.json');
      return;
    }

    try {
      let status = await this.push.checkPermissions();
      if (status.receive === 'prompt' || status.receive === 'prompt-with-rationale') {
        status = await this.push.requestPermissions();
      }
      // Denegado: no se insiste. Volver a pedirlo no muestra nada —el sistema
      // solo pregunta una vez— y a partir de ahí se cambia en los ajustes.
      if (status.receive !== 'granted') return;

      this.attachListeners();
      await this.push.register();
    } catch (error) {
      // Nada de esto puede impedir usar la aplicación: sin push, las
      // notificaciones se siguen viendo dentro.
      console.warn('No se pudo registrar el dispositivo para push', error);
    }
  }

  /** Da de baja el dispositivo. Se llama al cerrar sesión. */
  async unregister(): Promise<void> {
    if (!Capacitor.isNativePlatform() || !this.token) return;

    const token = this.token;
    this.token = null;
    try {
      // Cuerpo en un DELETE: es lo que espera el backend, y HttpClient solo
      // lo envía por la opción `body`.
      await this.http
        .delete(this.apiUrl, {
          body: { token, platform: this.platform() },
          context: new HttpContext().set(BACKGROUND_REQUEST, true),
        })
        .toPromise();
    } catch (error) {
      // Si falla, el servidor conserva el token hasta que FCM lo rechace y lo
      // limpie solo. Molesto, pero no impide cerrar sesión.
      console.warn('No se pudo dar de baja el dispositivo', error);
    }
    try {
      await this.push.removeAllListeners();
    } catch {
      // Ignorado: el plugin no está en web y esto corre también al cerrar
      // sesión desde el navegador.
    }
    this.listenersReady = false;
  }

  private platform(): 'ios' | 'android' {
    return Capacitor.getPlatform() === 'ios' ? 'ios' : 'android';
  }

  private attachListeners(): void {
    if (this.listenersReady) return;
    this.listenersReady = true;

    // El sistema devuelve el token por aquí, de forma asíncrona, después de
    // register(). No lo devuelve register() en sí.
    this.push.addListener('registration', (token: Token) => {
      this.token = token.value;
      this.sendToken(token.value);
    });

    this.push.addListener('registrationError', (error) => {
      console.warn('El sistema rechazó el registro para push', error);
    });

    // Llega con la aplicación en primer plano. El sistema no muestra nada en
    // ese caso, así que lo único útil es refrescar el contador: la
    // notificación ya está en la base de datos.
    this.push.addListener(
      'pushNotificationReceived',
      (notification: PushNotificationSchema) => this.zone.run(() => {
        this.notifications.loadUnreadCount();
        const target = notification.data as PushData | undefined;
        if (target?.resource_type === 'chat') {
          const alert = this.snackBar.open('Tienes un nuevo mensaje', 'Abrir', { duration: 5000 });
          alert.onAction().subscribe(() => openNotification(this.router, target));
        }
      })
    );

    // El usuario ha tocado el aviso.
    this.push.addListener(
      'pushNotificationActionPerformed',
      (action: ActionPerformed) => {
        this.notifications.loadUnreadCount();
        this.zone.run(() => openNotification(this.router, action.notification.data as PushData));
      }
    );
  }

  private sendToken(token: string): void {
    this.http
      .post(this.apiUrl, { token, platform: this.platform() }, { context: new HttpContext().set(BACKGROUND_REQUEST, true) })
      .subscribe({
        error: (error) =>
          console.warn('No se pudo enviar el token al servidor', error),
      });
  }
}
