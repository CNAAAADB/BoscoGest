import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { map, catchError, of } from 'rxjs';

export const permissionGuard = (resource: string, action: string): CanActivateFn => {
  return (route, state) => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (!authService.isLoggedIn()) {
      return router.createUrlTree(['/login']);
    }

    return authService.checkPermission(resource, action).pipe(
      map(hasPermission => {
        if (hasPermission) {
          return true;
        }
        // Redirect to dashboard if user doesn't have permission
        return router.createUrlTree(['/dashboard']);
      }),
      catchError(() => {
        // On error, redirect to dashboard
        return of(router.createUrlTree(['/dashboard']));
      })
    );
  };
};
