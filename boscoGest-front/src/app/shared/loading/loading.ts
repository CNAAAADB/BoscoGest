import { HttpContextToken, HttpInterceptorFn } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';

/**
 * Marks a request that must not block the screen.
 *
 * For writes that happen on their own or so often that freezing the app for
 * them would get in the way: registering the phone for push, marking a
 * notification as read, sending a chat message — blocking that one would stop
 * the next message being typed.
 */
export const BACKGROUND_REQUEST = new HttpContextToken<boolean>(() => false);

/** Methods that change something, and so must not be sent twice. */
const WRITES = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

/**
 * How many writes are on their way to the server.
 *
 * While there is one, LoadingOverlayComponent covers the screen. People tapped
 * "Guardar" or "Iniciar sesión" again when nothing seemed to happen, and every
 * tap was another request.
 */
@Injectable({ providedIn: 'root' })
export class LoadingService {
  private readonly pending = signal(0);
  readonly busy = computed(() => this.pending() > 0);

  start(): void {
    this.pending.update((n) => n + 1);
  }

  stop(): void {
    this.pending.update((n) => Math.max(0, n - 1));
  }
}

/**
 * Counts writes in and out. Reads are left alone: lists load in the
 * background, notifications are polled, and none of that is harmful to repeat.
 */
export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  if (!WRITES.has(req.method) || req.context.get(BACKGROUND_REQUEST)) {
    return next(req);
  }
  const loading = inject(LoadingService);
  loading.start();
  // finalize covers success, error and cancellation alike, so the screen
  // cannot stay blocked after a request is over.
  return next(req).pipe(finalize(() => loading.stop()));
};
