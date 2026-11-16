import { Injectable, inject } from '@angular/core';
import { HttpBackend, HttpClient } from '@angular/common/http';
import { defer, finalize, from, map, Observable, of, shareReplay, switchMap, catchError, tap } from 'rxjs';
import { environment } from '../../environments/environment';
import { SessionCredentialService } from './session-credential.service';

export interface SessionTokens {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
}

/** Single-flight refresh, without interceptors, to prevent 401 recursion. */
@Injectable({ providedIn: 'root' })
export class SessionRefreshService {
  private readonly http = new HttpClient(inject(HttpBackend));
  private readonly credentials = inject(SessionCredentialService);
  private readonly url = environment.apiUrl;
  private pending: Observable<string | null> | null = null;

  renew(): Observable<string | null> {
    if (this.pending) return this.pending;
    const request$ = defer(() => from(this.credentials.retrieve())).pipe(
      switchMap((secret) => {
        if (this.credentials.native && !secret) return of(null);
        return this.http.post<SessionTokens>(
          `${this.url}/auth/refresh`,
          this.credentials.native ? { refresh_token: secret } : {},
          { withCredentials: !this.credentials.native }
        ).pipe(
          switchMap((tokens) => from(this.credentials.persist(tokens.refresh_token)).pipe(
            map(() => tokens.access_token)
          ))
        );
      }),
      tap((token) => {
        if (token) localStorage.setItem('authToken', token);
      }),
      catchError(() => of(null)),
      finalize(() => { this.pending = null; }),
      shareReplay({ bufferSize: 1, refCount: false })
    );
    this.pending = request$;
    return request$;
  }

  async revoke(): Promise<void> {
    const secret = await this.credentials.retrieve();
    try {
      await new Promise<void>((resolve) => {
        this.http.post<void>(
          `${this.url}/auth/session/revoke`,
          this.credentials.native ? { refresh_token: secret } : {},
          { withCredentials: !this.credentials.native }
        ).subscribe({ next: () => resolve(), error: () => resolve() });
      });
    } finally {
      await this.credentials.clear();
    }
  }
}
