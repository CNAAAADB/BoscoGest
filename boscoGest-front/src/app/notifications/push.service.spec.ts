import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { Capacitor } from '@capacitor/core';

import { PushService, PUSH_PLUGIN } from './push.service';
import { NotificationService } from './notification.service';
import { provideAppTesting } from '../testing/test-providers';
import { environment } from '../../environments/environment';

/**
 * El envío real no se puede probar aquí —hace falta un dispositivo y un
 * proyecto de Firebase—, pero sí todo lo que lo rodea: que en web no se toque
 * nada, que un permiso denegado no insista, y que al tocar un aviso se abra la
 * pantalla correcta.
 */
describe('PushService', () => {
  let service: PushService;
  let httpMock: HttpTestingController;
  let router: Router;
  /** Los callbacks que el servicio registra en el plugin, para dispararlos. */
  let listeners: Record<string, (arg: unknown) => void>;
  /** Doble del plugin. Capacitor lo expone tras un proxy que no admite spyOn,
   *  por eso el servicio lo recibe inyectado. */
  let plugin: {
    checkPermissions: jasmine.Spy;
    requestPermissions: jasmine.Spy;
    register: jasmine.Spy;
    addListener: jasmine.Spy;
    removeAllListeners: jasmine.Spy;
  };

  const devicesUrl = `${environment.apiUrl}/notifications/devices`;

  beforeEach(() => {
    listeners = {};
    plugin = {
      checkPermissions: jasmine.createSpy('checkPermissions'),
      requestPermissions: jasmine.createSpy('requestPermissions'),
      register: jasmine.createSpy('register').and.returnValue(Promise.resolve()),
      addListener: jasmine.createSpy('addListener').and.callFake(
        (name: string, cb: (arg: unknown) => void) => {
          listeners[name] = cb;
          return Promise.resolve({ remove: () => Promise.resolve() });
        }
      ),
      removeAllListeners: jasmine
        .createSpy('removeAllListeners')
        .and.returnValue(Promise.resolve()),
    };

    TestBed.configureTestingModule({
      providers: [
        provideAppTesting(),
        { provide: PUSH_PLUGIN, useValue: plugin },
        {
          provide: NotificationService,
          useValue: jasmine.createSpyObj('NotificationService', ['loadUnreadCount']),
        },
      ],
    });

    service = TestBed.inject(PushService);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate');
  });

  afterEach(() => httpMock.verify());

  /** Finge estar en un móvil, con el permiso en el estado indicado. */
  function onNative(receive: 'granted' | 'denied' | 'prompt') {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
    spyOn(Capacitor, 'getPlatform').and.returnValue('ios');
    plugin.checkPermissions.and.returnValue(Promise.resolve({ receive }));
    // Tras preguntar, el sistema concede salvo que el test diga lo contrario.
    plugin.requestPermissions.and.returnValue(
      Promise.resolve({ receive: receive === 'prompt' ? 'granted' : receive })
    );
  }

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('en web no toca el plugin', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(false);

    await service.register();

    // El plugin no existe en el navegador: llamarlo reventaría.
    expect(plugin.register).not.toHaveBeenCalled();
  });

  it('registra el dispositivo cuando hay permiso', async () => {
    onNative('granted');

    await service.register();

    expect(plugin.register).toHaveBeenCalled();
  });

  describe('en Android', () => {
    const original = environment.androidPush;
    afterEach(() => (environment.androidPush = original));

    beforeEach(() => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
      spyOn(Capacitor, 'getPlatform').and.returnValue('android');
      plugin.checkPermissions.and.returnValue(Promise.resolve({ receive: 'granted' }));
    });

    it('no toca el plugin si la compilación no lleva Firebase', async () => {
      // Sin google-services.json, register() lanza en Java y cierra la app.
      environment.androidPush = false;

      await service.register();

      expect(plugin.checkPermissions).not.toHaveBeenCalled();
      expect(plugin.register).not.toHaveBeenCalled();
    });

    it('registra el dispositivo si la lleva', async () => {
      environment.androidPush = true;

      await service.register();

      expect(plugin.register).toHaveBeenCalled();
    });
  });

  it('no registra si se deniega el permiso', async () => {
    onNative('denied');

    await service.register();

    // El sistema solo pregunta una vez; insistir no muestra nada.
    expect(plugin.register).not.toHaveBeenCalled();
  });

  it('pide permiso cuando aún no se ha preguntado', async () => {
    onNative('prompt');

    await service.register();

    expect(plugin.requestPermissions).toHaveBeenCalled();
  });

  it('manda el token al servidor cuando el sistema lo entrega', async () => {
    onNative('granted');
    await service.register();

    listeners['registration']({ value: 'token-del-sistema' });

    const req = httpMock.expectOne(devicesUrl);
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      token: 'token-del-sistema',
      platform: 'ios',
    });
    req.flush({ id: 1, platform: 'ios', created_at: '2026-09-23T10:00:00Z' });
  });

  it('da de baja el token al cerrar sesión', async () => {
    onNative('granted');
    await service.register();
    listeners['registration']({ value: 'token-a-dar-de-baja' });
    httpMock.expectOne(devicesUrl).flush({});

    const promesa = service.unregister();

    const req = httpMock.expectOne(devicesUrl);
    expect(req.request.method).toBe('DELETE');
    // El backend espera el token en el cuerpo del DELETE.
    expect(req.request.body).toEqual({
      token: 'token-a-dar-de-baja',
      platform: 'ios',
    });
    req.flush({});
    await promesa;
  });

  it('no llama al servidor si no hay token que dar de baja', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);

    await service.unregister();

    httpMock.expectNone(devicesUrl);
  });

  describe('al tocar un aviso', () => {
    beforeEach(async () => {
      onNative('granted');
      await service.register();
    });

    function tap(data: Record<string, string>) {
      listeners['pushNotificationActionPerformed']({ notification: { data } });
    }

    it('abre exactamente la solicitud o la conversación del aviso', () => {
      tap({ resource_type: 'membership_requests', resource_id: '8', event_type: 'membership_request_created' });
      expect(router.navigate).toHaveBeenCalledWith(['/membership-requests'], { queryParams: { request: '8' } });
      tap({ resource_type: 'chat', resource_id: '12' });
      expect(router.navigate).toHaveBeenCalledWith(['/chat'], { queryParams: { conversation: '12' } });
    });

    it('abre el recurso que lo originó', () => {
      tap({ resource_type: 'activities', resource_id: '7' });
      expect(router.navigate).toHaveBeenCalledWith(['/activities', '7']);
    });

    it('lleva al panel de inicio en las membresías, que no tienen pantalla propia', () => {
      tap({ resource_type: 'memberships', resource_id: '3' });
      expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
    });

    it('no navega si el tipo de recurso no tiene pantalla', () => {
      tap({ resource_type: 'fees', resource_id: '4' });
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('no navega sin identificador de recurso', () => {
      tap({ resource_type: 'activities' });
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('refresca el contador aunque no navegue', () => {
      const notifications = TestBed.inject(
        NotificationService
      ) as jasmine.SpyObj<NotificationService>;
      tap({ resource_type: 'fees' });
      expect(notifications.loadUnreadCount).toHaveBeenCalled();
    });
  });

  it('refresca el contador con un aviso en primer plano', async () => {
    onNative('granted');
    await service.register();
    const notifications = TestBed.inject(
      NotificationService
    ) as jasmine.SpyObj<NotificationService>;

    // El sistema no muestra nada con la app abierta: lo único útil es el
    // contador, porque la notificación ya está guardada.
    listeners['pushNotificationReceived']({ title: 'Hola' });

    expect(notifications.loadUnreadCount).toHaveBeenCalled();
  });
});
