import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { Subject } from 'rxjs';
import { Capacitor } from '@capacitor/core';
import { environment } from '../../environments/environment';
import {
  NotificationResponse,
  UnreadCountResponse,
  NotificationPreferenceResponse,
  NotificationPreferencesUpdate,
} from '../models/user.model';
import { BACKGROUND_REQUEST } from '../shared/loading/loading';

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private apiUrl = `${environment.apiUrl}/notifications`;
  private wsUrl = `${environment.wsUrl}/notifications/ws`;

  readonly notifications = signal<NotificationResponse[]>([]);
  readonly unreadCount = signal<number>(0);
  readonly notificationReceived$ = new Subject<NotificationResponse>();

  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private intentionalClose = false;

  constructor(private http: HttpClient) {
    const token = localStorage.getItem('authToken');
    if (token) {
      this.connect();
      this.loadUnreadCount();
    }
  }

  // ── WebSocket ──────────────────────────────────────────

  connect(): void {
    const token = localStorage.getItem('authToken');
    if (!token) return;

    // On native platforms (iOS/Android), ws:// is blocked as mixed content
    // because the app is served via https://localhost. Use polling instead.
    if (Capacitor.isNativePlatform()) {
      this.startPolling();
      return;
    }

    // Constructor and session validation may both call connect while the
    // handshake is in flight. Reuse the same socket in that case.
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) return;

    this.intentionalClose = false;
    this.ws = new WebSocket(`${this.wsUrl}?token=${token}`);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startPing();
    };

    this.ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const notification: NotificationResponse = JSON.parse(event.data);
        this.notifications.update((list) => [notification, ...list]);
        this.unreadCount.update((c) => c + 1);
        this.notificationReceived$.next(notification);
      } catch {
        // ignore non-JSON messages
      }
    };

    this.ws.onclose = () => {
      this.stopPing();
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.stopPing();
    this.stopPolling();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.reconnectAttempts = 0;
    this.notifications.set([]);
    this.unreadCount.set(0);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  // ── Polling (native platforms) ─────────────────────────

  private startPolling(): void {
    this.stopPolling();
    this.pollTimer = setInterval(() => this.loadUnreadCount(), 30000);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  // ── REST ───────────────────────────────────────────────

  loadNotifications(skip = 0, limit = 50): void {
    this.http
      .get<NotificationResponse[]>(this.apiUrl, {
        params: { skip: skip.toString(), limit: limit.toString() },
      })
      .subscribe({
        next: (data) => this.notifications.set(data),
      });
  }

  loadUnreadCount(): void {
    this.http
      .get<UnreadCountResponse>(`${this.apiUrl}/unread-count`)
      .subscribe({
        next: (data) => this.unreadCount.set(data.count),
      });
  }

  markAsRead(id: number): void {
    // Background: tapping a notification should open it, not freeze the screen.
    this.http.put<NotificationResponse>(`${this.apiUrl}/${id}/read`, {}, { context: new HttpContext().set(BACKGROUND_REQUEST, true) }).subscribe({
      next: () => {
        this.notifications.update((list) =>
          list.map((n) => (n.id === id ? { ...n, is_read: true } : n))
        );
        this.unreadCount.update((c) => Math.max(0, c - 1));
      },
    });
  }

  markAllAsRead(): void {
    this.http.put<{ marked: number }>(`${this.apiUrl}/read-all`, {}, { context: new HttpContext().set(BACKGROUND_REQUEST, true) }).subscribe({
      next: () => {
        this.notifications.update((list) =>
          list.map((n) => ({ ...n, is_read: true }))
        );
        this.unreadCount.set(0);
      },
    });
  }

  deleteNotification(id: number): void {
    this.http.delete(`${this.apiUrl}/${id}`, { context: new HttpContext().set(BACKGROUND_REQUEST, true) }).subscribe({
      next: () => {
        const removed = this.notifications().find((n) => n.id === id);
        this.notifications.update((list) => list.filter((n) => n.id !== id));
        if (removed && !removed.is_read) {
          this.unreadCount.update((c) => Math.max(0, c - 1));
        }
      },
    });
  }

  getPreferences() {
    return this.http.get<NotificationPreferenceResponse[]>(
      `${this.apiUrl}/preferences`
    );
  }

  updatePreferences(data: NotificationPreferencesUpdate) {
    return this.http.put<NotificationPreferenceResponse[]>(
      `${this.apiUrl}/preferences`,
      data
    );
  }

  getEventTypes() {
    return this.http.get<{ event_type: string; label: string }[]>(
      `${this.apiUrl}/event-types`
    );
  }
}
