import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of, map, switchMap, forkJoin } from 'rxjs';
import { environment } from '../../environments/environment';
import { UserResponse, MembershipDetails, PermissionResponse } from '../models/user.model';
import { BrandingService } from '../settings/branding.service';
import { NotificationService } from '../notifications/notification.service';
import { PushService } from '../notifications/push.service';

interface TokenResponse {
  access_token: string;
  token_type: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private isAuthenticated = signal<boolean>(false);
  private currentUser = signal<UserResponse | null>(null);
  private currentMembership = signal<MembershipDetails | null>(null);
  private allMemberships = signal<MembershipDetails[]>([]);
  private apiUrl = environment.apiUrl;

  // Computed signal with unique permissions from all memberships
  private allUniquePermissions = computed<PermissionResponse[]>(() => {
    const memberships = this.allMemberships();
    const permissionsMap = new Map<string, PermissionResponse>();

    memberships.forEach(membership => {
      if (membership.role?.permissions) {
        membership.role.permissions.forEach(permission => {
          const key = `${permission.resource}:${permission.action}`;
          if (!permissionsMap.has(key)) {
            permissionsMap.set(key, permission);
          }
        });
      }
    });

    return Array.from(permissionsMap.values());
  });

  constructor(
    private router: Router,
    private http: HttpClient,
    private brandingService: BrandingService
  ) {
    // Check if user is already logged in (from localStorage)
    const token = localStorage.getItem('authToken');
    if (token) {
      this.validateToken();
    }
  }

  /**
   * What a session needs: the person and their memberships, fetched together.
   *
   * The person comes from /users/me, not from the first membership. Someone
   * who has just signed up has no membership until their request is approved,
   * and taking the user from there left them with an empty profile — no name,
   * no DNI, "Invalid Date" — right after typing all of it in.
   */
  private loadSession(): Observable<void> {
    return forkJoin({
      memberships: this.http.get<MembershipDetails[]>(`${this.apiUrl}/memberships`),
      me: this.http.get<UserResponse>(`${this.apiUrl}/users/me`),
    }).pipe(
      map(({ memberships, me }) => {
        this.currentUser.set(me);
        if (memberships && memberships.length > 0) {
          this.allMemberships.set(memberships);
          this.currentMembership.set(memberships[0]);
          this.loadEntityBranding(memberships[0].entity_id);
        } else {
          // No membership yet = pending approval. Still a valid session.
          this.allMemberships.set([]);
        }
      })
    );
  }

  private validateToken(): void {
    this.loadSession().subscribe({
      next: () => {
        // Token is valid regardless of whether user has memberships
        this.isAuthenticated.set(true);
      },
      error: (error) => {
        console.error('Token validation failed:', error);
        this.clearAuthData();
      }
    });
  }

  checkAuth(): Observable<boolean> {
    const token = localStorage.getItem('authToken');
    if (!token) {
      return of(false);
    }

    if (this.isAuthenticated()) {
      return of(true);
    }

    return this.loadSession().pipe(
      map(() => {
        // Token valid — authenticate regardless of memberships count
        this.isAuthenticated.set(true);
        return true;
      }),
      catchError((error) => {
        console.error('Token validation failed:', error);
        this.clearAuthData();
        return of(false);
      })
    );
  }

  login(identifier: string, password: string): Observable<boolean> {
    const formData = new FormData();
    formData.append('identifier', identifier);
    formData.append('password', password);

    return this.http.post<TokenResponse>(`${this.apiUrl}/auth/token`, formData).pipe(
      switchMap((response) => this.adoptSession(response.access_token)),
      catchError((error) => {
        console.error('Login error:', error);
        this.isAuthenticated.set(false);
        return of(false);
      })
    );
  }

  /**
   * Exchange a one-shot link from a welcome email for a session.
   *
   * People an administrator created never learn their password, so this is how
   * they get in the first time. What comes back is an ordinary session, and the
   * account still carries must_change_password, which is what sends them
   * straight to choosing one.
   *
   * Errors are passed through untouched: the reason the link failed decides
   * what the screen offers next.
   */
  activateWithToken(token: string): Observable<boolean> {
    return this.http
      .post<TokenResponse>(`${this.apiUrl}/auth/activate`, { token })
      .pipe(switchMap((response) => this.adoptSession(response.access_token)));
  }

  /** Ask for a fresh link. Always succeeds, whoever the address belongs to. */
  resendActivation(identifier: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(
      `${this.apiUrl}/auth/activate/resend`,
      { identifier }
    );
  }

  /**
   * Store an access token and load what the session needs from it.
   *
   * Shared by the password login and by the activation links, so a session
   * ends up in the same state however it was opened.
   */
  private adoptSession(accessToken: string): Observable<boolean> {
    localStorage.setItem('authToken', accessToken);
    this.isAuthenticated.set(true);

    return this.loadSession().pipe(
      map(() => true),
      // Aquí, y no en login(), porque el enlace de activación entra por el
      // mismo sitio: quien estrena cuenta también debe recibir avisos.
      tap(() => void this.pushService.register())
    );
  }

  logout(): void {
    // La baja del dispositivo va primero: es una petición autenticada y el
    // logout revoca el token. Sin esperarla, porque cerrar sesión no puede
    // quedarse colgado si el servidor no responde; si se pierde, el token se
    // limpiará solo cuando FCM lo rechace.
    void this.pushService.unregister();

    this.http.post(`${this.apiUrl}/auth/logout`, {}).subscribe({
      next: () => {
        this.clearAuthData();
      },
      error: (error) => {
        console.error('Logout error:', error);
        this.clearAuthData();
      }
    });
  }

  /**
   * Cierra la sesión sin pasar por el backend.
   *
   * Para cuando el servidor ya ha revocado el token — al eliminar la cuenta,
   * por ejemplo — y pedirle un logout solo devolvería un 401.
   */
  endSession(): void {
    // Sin dar de baja el dispositivo contra el servidor: el token ya está
    // revocado y la petición daría 401. Al eliminar la cuenta, el backend
    // borra sus dispositivos por su cuenta.
    this.clearAuthData();
  }

  private notificationService = inject(NotificationService);
  private pushService = inject(PushService);

  private clearAuthData(): void {
    this.notificationService.disconnect();
    localStorage.removeItem('authToken');
    this.isAuthenticated.set(false);
    this.currentUser.set(null);
    this.currentMembership.set(null);
    this.allMemberships.set([]);
    this.brandingService.resetBrandingToDefault();
    this.router.navigate(['/login']);
  }

  private loadEntityBranding(entityId: number): void {
    this.brandingService.getEntityBranding(entityId).subscribe({
      next: (branding) => {
        this.brandingService.applyBrandingToDOM(branding);
      },
      error: (error) => {
        if (error.status !== 404) {
          console.error('Error loading branding:', error);
        }
        this.brandingService.resetBrandingToDefault();
      }
    });
  }

  isLoggedIn(): boolean {
    return this.isAuthenticated();
  }

  hasMemberships(): boolean {
    return this.allMemberships().length > 0;
  }

  getCurrentUser(): UserResponse | null {
    return this.currentUser();
  }

  getCurrentMembership(): MembershipDetails | null {
    return this.currentMembership();
  }

  hasPermission(resource: string, action: string): boolean {
    const permissions = this.allUniquePermissions();
    return permissions.some(
      permission => permission.resource === resource && permission.action === action
    );
  }

  hasEntityPermission(entityId: number, action: string): boolean {
    const memberships = this.allMemberships();

    const hasManageAll = memberships.some(membership =>
      membership.role?.permissions?.some(
        permission => permission.resource === 'entities' && permission.action === 'manage_all'
      )
    );

    if (hasManageAll) {
      return true;
    }

    return memberships.some(membership =>
      membership.entity_id === entityId &&
      membership.role?.permissions?.some(
        permission => permission.resource === 'entities' && permission.action === action
      )
    );
  }

  /**
   * Si se tiene un permiso **en una asociación concreta**.
   *
   * Para los permisos no heredables —`memberships:*`, `roles:create/update/
   * delete/assign`, `branding:*`, `views:*`, `entities:create/update/delete`—,
   * que solo valen en la asociación donde se tienen y no caen hacia los hijos.
   * `hasPermission()` no sirve aquí: mira todos los permisos juntos y diría que
   * sí por tenerlo en otra asociación cualquiera.
   *
   * Es una pista para la interfaz, no el control de acceso: quien decide es el
   * backend, con `check_entity_permission`. Sirve para no enseñar un botón que
   * va a devolver 403.
   */
  hasPermissionAtEntity(entityId: number, resource: string, action: string): boolean {
    return this.allMemberships().some((membership) => {
      if (!membership.is_active) return false;
      const permisos = membership.role?.permissions ?? [];
      // manage_all sobre el recurso vale en cualquier asociación.
      if (permisos.some((p) => p.resource === resource && p.action === 'manage_all')) {
        return true;
      }
      return (
        membership.entity_id === entityId &&
        permisos.some((p) => p.resource === resource && p.action === action)
      );
    });
  }

  hasAnyPermissionForResource(resource: string): boolean {
    const permissions = this.allUniquePermissions();
    return permissions.some(
      permission => permission.resource === resource
    );
  }

  getCurrentPermissions(): string[] {
    const permissions = this.allUniquePermissions();
    return permissions.map(
      permission => `${permission.resource}:${permission.action}`
    );
  }

  getAllMemberships(): MembershipDetails[] {
    return this.allMemberships();
  }

  checkPermission(resource: string, action: string, resourceId?: number): Observable<boolean> {
    const params: any = { resource, action };
    if (resourceId !== undefined) {
      params.resource_id = resourceId;
    }

    return this.http.get<any>(`${this.apiUrl}/auth/check-permission`, { params }).pipe(
      map(() => true),
      catchError((error) => {
        console.error('Permission check error:', error);
        if (error.status === 401) {
          this.clearAuthData();
        }
        return of(false);
      })
    );
  }
}
