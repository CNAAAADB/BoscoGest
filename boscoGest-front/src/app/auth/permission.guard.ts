import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { map, catchError, of } from 'rxjs';

/**
 * Lets a route open only for whoever holds `resource:action`.
 *
 * It used to ask the backend (/auth/check-permission) and took any 200 as a
 * yes — but that endpoint always answers 200, with the verdict in the body, so
 * every signed-in user got through every guarded route and found out at the
 * first request. It now decides from the session's own permissions, the same
 * ones the sidebar uses to show the entry, so the menu and the route agree.
 *
 * `scope: 'root'` is for platform-wide pages (fee maintenance), which the
 * backend only allows to whoever holds the permission at the root entity.
 *
 * Still only a hint for the interface: the backend checks every request.
 */
export const permissionGuard = (
  resource: string,
  action: string,
  scope: 'any' | 'root' = 'any',
): CanActivateFn => {
  return () => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (!authService.isLoggedIn()) {
      return router.createUrlTree(['/login']);
    }

    // After a reload the memberships may not be in yet; checkAuth waits for
    // them (and returns at once if they already are).
    return authService.checkAuth().pipe(
      map((authenticated) => {
        if (!authenticated) {
          return router.createUrlTree(['/login']);
        }
        const allowed = scope === 'root'
          ? authService.hasRootPermission(resource, action)
          : authService.canPerform(resource, action);
        return allowed ? true : router.createUrlTree(['/dashboard']);
      }),
      // A network error must not leave the navigation hanging.
      catchError(() => of(router.createUrlTree(['/dashboard'])))
    );
  };
};
