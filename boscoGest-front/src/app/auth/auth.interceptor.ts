import { inject } from '@angular/core';
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, switchMap, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { SessionRefreshService } from './session-refresh.service';

const NO_REFRESH = ['/auth/token', '/auth/refresh', '/auth/session/revoke'];

/** Attach the short-lived JWT and retry an expired token only once. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!req.url.startsWith(environment.apiUrl)) return next(req);

  const token = localStorage.getItem('authToken');
  const request = token && !req.url.includes('/auth/token')
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  // Requests used to obtain or revoke credentials are never retried.
  if (NO_REFRESH.some((path) => req.url.includes(path))) return next(request);

  const sessions = inject(SessionRefreshService);
  return next(request).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status !== 401) return throwError(() => err);
      return sessions.renew().pipe(
        switchMap((newToken) => newToken
          ? next(req.clone({
              setHeaders: { Authorization: `Bearer ${newToken}` }
            }))
          : throwError(() => err)
        )
      );
    })
  );
};
