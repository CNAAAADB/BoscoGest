import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, catchError, of, map, switchMap } from 'rxjs';
import { environment } from '../../environments/environment';
import { UserResponse, MembershipDetails, PermissionResponse } from '../models/user.model';
import { BrandingService } from '../settings/branding.service';
import { NotificationService } from '../notifications/notification.service';

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
      // Validate token by attempting to load user data
      this.validateToken();
    }
  }

  private validateToken(): void {
    this.http.get<MembershipDetails[]>(`${this.apiUrl}/memberships`).subscribe({
      next: (memberships) => {
        if (memberships && memberships.length > 0) {
          this.isAuthenticated.set(true);
          this.allMemberships.set(memberships); // Store all memberships
          this.currentMembership.set(memberships[0]); // Use first membership for entity context
          if (memberships[0].user) {
            this.currentUser.set(memberships[0].user);
          }
          // Load branding for the current entity
          this.loadEntityBranding(memberships[0].entity_id);
        } else {
          this.clearAuthData();
        }
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

    // If already validated and authenticated, return true
    if (this.isAuthenticated()) {
      return of(true);
    }

    // Validate token by attempting to load user data
    return this.http.get<MembershipDetails[]>(`${this.apiUrl}/memberships`).pipe(
      map((memberships) => {
        if (memberships && memberships.length > 0) {
          this.isAuthenticated.set(true);
          this.allMemberships.set(memberships); // Store all memberships
          this.currentMembership.set(memberships[0]); // Use first membership for entity context
          if (memberships[0].user) {
            this.currentUser.set(memberships[0].user);
          }
          // Load branding for the current entity
          this.loadEntityBranding(memberships[0].entity_id);
          return true;
        }
        this.clearAuthData();
        return false;
      }),
      catchError((error) => {
        console.error('Token validation failed:', error);
        this.clearAuthData();
        return of(false);
      })
    );
  }

  private loadUserData(): void {
    // Load all user memberships
    this.http.get<MembershipDetails[]>(`${this.apiUrl}/memberships`).subscribe({
      next: (memberships) => {
        if (memberships && memberships.length > 0) {
          this.allMemberships.set(memberships); // Store all memberships
          this.currentMembership.set(memberships[0]); // Use first membership for entity context
          if (memberships[0].user) {
            this.currentUser.set(memberships[0].user);
          }
          // Load branding for the current entity
          this.loadEntityBranding(memberships[0].entity_id);
        }
      },
      error: (error) => {
        console.error('Error loading user data:', error);
      }
    });
  }

  login(email: string, password: string): Observable<boolean> {
    // FastAPI OAuth2 expects form data with 'email' and 'password' fields
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);

    return this.http.post<TokenResponse>(`${this.apiUrl}/auth/token`, formData).pipe(
      tap((response) => {
        localStorage.setItem('authToken', response.access_token);
        this.isAuthenticated.set(true);
      }),
      switchMap(() => {
        // Load user data after successful login
        this.loadUserData();
        return of(true);
      }),
      catchError((error) => {
        console.error('Login error:', error);
        this.isAuthenticated.set(false);
        return of(false);
      })
    );
  }

  logout(): void {
    // Call backend logout endpoint
    this.http.post(`${this.apiUrl}/auth/logout`, {}).subscribe({
      next: () => {
        this.clearAuthData();
      },
      error: (error) => {
        console.error('Logout error:', error);
        // Clear local data even if backend call fails
        this.clearAuthData();
      }
    });
  }

  private notificationService = inject(NotificationService);

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
        // If no branding configured (404), use defaults
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

  getCurrentUser(): UserResponse | null {
    return this.currentUser();
  }

  getCurrentMembership(): MembershipDetails | null {
    return this.currentMembership();
  }

  /**
   * Check if the current user has a specific permission across all their memberships.
   * This is a synchronous check that looks at the loaded permissions in memory.
   * For server-side validation, use checkPermission() instead.
   */
  hasPermission(resource: string, action: string): boolean {
    const permissions = this.allUniquePermissions();
    return permissions.some(
      permission => permission.resource === resource && permission.action === action
    );
  }

  /**
   * Check if the current user has permission to perform an action on a specific entity.
   * Returns true if:
   * - User has 'entities:manage_all' permission (can manage any entity), OR
   * - User has a membership in the specific entity with the required permission
   */
  hasEntityPermission(entityId: number, action: string): boolean {
    const memberships = this.allMemberships();

    // First check if user has manage_all permission
    const hasManageAll = memberships.some(membership =>
      membership.role?.permissions?.some(
        permission => permission.resource === 'entities' && permission.action === 'manage_all'
      )
    );

    if (hasManageAll) {
      return true;
    }

    // Check if user has membership in this specific entity with the required permission
    return memberships.some(membership =>
      membership.entity_id === entityId &&
      membership.role?.permissions?.some(
        permission => permission.resource === 'entities' && permission.action === action
      )
    );
  }

  /**
   * Check if the current user has any permission for a specific resource across all their memberships.
   */
  hasAnyPermissionForResource(resource: string): boolean {
    const permissions = this.allUniquePermissions();
    return permissions.some(
      permission => permission.resource === resource
    );
  }

  /**
   * Get all unique permissions across all the current user's memberships.
   */
  getCurrentPermissions(): string[] {
    const permissions = this.allUniquePermissions();
    return permissions.map(
      permission => `${permission.resource}:${permission.action}`
    );
  }

  /**
   * Get all memberships for the current user.
   */
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
        // If 401 Unauthorized, clear auth data and redirect to login
        if (error.status === 401) {
          this.clearAuthData();
        }
        return of(false);
      })
    );
  }
}
