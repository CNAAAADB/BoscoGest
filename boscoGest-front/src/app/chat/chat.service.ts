import { Injectable, signal } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Capacitor } from '@capacitor/core';
import { environment } from '../../environments/environment';
import {
  ChatMessage,
  ChatMember,
  ChatWsPayload,
  ConversationDetail,
  ConversationListItem,
  JoinRequest,
  UserSearchResult,
} from '../models/chat.model';
import { BACKGROUND_REQUEST } from '../shared/loading/loading';

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private apiUrl = `${environment.apiUrl}/chat`;
  private wsUrl = `${environment.wsUrl}/chat/ws`;

  readonly conversations = signal<ConversationListItem[]>([]);
  readonly totalUnread = signal<number>(0);
  readonly pendingConversationId = signal<number | null>(null);

  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private intentionalClose = false;

  // Callback for incoming payloads — set by ConversationViewComponent
  onMessage: ((payload: ChatWsPayload) => void) | null = null;

  constructor(private http: HttpClient) {
    const token = localStorage.getItem('authToken');
    if (token) {
      this.connect();
      this.loadConversations();
    }
  }

  // ── WebSocket ──────────────────────────────────────────────────────

  connect(): void {
    const token = localStorage.getItem('authToken');
    if (!token) return;

    if (Capacitor.isNativePlatform()) return; // no WS on native

    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.intentionalClose = false;
    this.ws = new WebSocket(`${this.wsUrl}?token=${token}`);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startPing();
    };

    this.ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const payload: ChatWsPayload = JSON.parse(event.data);
        this.handleWsPayload(payload);
      } catch {
        // ignore non-JSON
      }
    };

    this.ws.onclose = () => {
      this.stopPing();
      if (!this.intentionalClose) this.scheduleReconnect();
    };

    this.ws.onerror = () => this.ws?.close();
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.reconnectAttempts = 0;
    this.conversations.set([]);
    this.totalUnread.set(0);
  }

  sendTyping(conversationId: number): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'typing', conversation_id: conversationId }));
    }
  }

  private handleWsPayload(payload: ChatWsPayload): void {
    if (payload.type === 'new_message') {
      this.conversations.update((list) => {
        const updated = list.map((c) => {
          if (c.id !== payload.conversation_id) return c;
          return {
            ...c,
            last_message: {
              id: payload.message.id,
              content: payload.message.content,
              sender: payload.message.sender,
              created_at: payload.message.created_at,
              is_deleted: false,
              message_type: payload.message.message_type,
            },
            // Only increment unread for non-system messages
            unread_count: payload.message.message_type !== 'system'
              ? c.unread_count + 1
              : c.unread_count,
          };
        });
        // Keep pinned conversations on top
        return [...updated].sort((a, b) => {
          if (a.is_pinned && !b.is_pinned) return -1;
          if (!a.is_pinned && b.is_pinned) return 1;
          return 0;
        });
      });
      if (payload.message.message_type !== 'system') {
        this.totalUnread.update((n) => n + 1);
      }
    } else if (
      payload.type === 'added_to_group' ||
      payload.type === 'join_request_accepted'
    ) {
      this.loadConversations();
    }
    // Forward all payloads to the active conversation view
    this.onMessage?.(payload);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) this.ws.send('ping');
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

  // ── Conversations ──────────────────────────────────────────────────

  loadConversations(): void {
    this.http
      .get<ConversationListItem[]>(`${this.apiUrl}/conversations`)
      .subscribe({
        next: (data) => {
          // Pinned first
          const sorted = [...data].sort((a, b) => {
            if (a.is_pinned && !b.is_pinned) return -1;
            if (!a.is_pinned && b.is_pinned) return 1;
            return 0;
          });
          this.conversations.set(sorted);
          this.totalUnread.set(data.reduce((acc, c) => acc + c.unread_count, 0));
        },
      });
  }

  getConversations(): Observable<ConversationListItem[]> {
    return this.http.get<ConversationListItem[]>(`${this.apiUrl}/conversations`);
  }

  getOrCreateDirect(targetUserId: number): Observable<ConversationListItem> {
    return this.http.post<ConversationListItem>(
      `${this.apiUrl}/conversations/direct`,
      { target_user_id: targetUserId }
    );
  }

  createGroup(name: string, description?: string): Observable<ConversationListItem> {
    return this.http.post<ConversationListItem>(
      `${this.apiUrl}/conversations/group`,
      { name, description }
    );
  }

  getConversationDetail(id: number): Observable<ConversationDetail> {
    return this.http.get<ConversationDetail>(`${this.apiUrl}/conversations/${id}`);
  }

  updateGroup(
    id: number,
    data: { name?: string; description?: string }
  ): Observable<ConversationDetail> {
    return this.http.put<ConversationDetail>(
      `${this.apiUrl}/conversations/${id}`,
      data
    );
  }

  deleteGroup(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/conversations/${id}`);
  }

  uploadGroupAvatar(id: number, file: File): Observable<ConversationDetail> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ConversationDetail>(
      `${this.apiUrl}/conversations/${id}/avatar`,
      formData
    );
  }

  muteConversation(id: number): Observable<void> {
    return this.http.put<void>(`${this.apiUrl}/conversations/${id}/mute`, {});
  }

  unmuteConversation(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/conversations/${id}/mute`);
  }

  pinConversation(id: number): Observable<void> {
    return this.http.put<void>(`${this.apiUrl}/conversations/${id}/pin`, {});
  }

  unpinConversation(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/conversations/${id}/pin`);
  }

  // ── Messages ───────────────────────────────────────────────────────

  getMessages(
    conversationId: number,
    beforeId?: number,
    limit = 50
  ): Observable<ChatMessage[]> {
    const params: Record<string, string> = { limit: limit.toString() };
    if (beforeId !== undefined) params['before_id'] = beforeId.toString();
    return this.http.get<ChatMessage[]>(
      `${this.apiUrl}/conversations/${conversationId}/messages`,
      { params }
    );
  }

  searchMessages(conversationId: number, query: string): Observable<ChatMessage[]> {
    return this.http.get<ChatMessage[]>(
      `${this.apiUrl}/conversations/${conversationId}/messages/search`,
      { params: { q: query } }
    );
  }

  sendMessage(
    conversationId: number,
    content: string,
    replyToId?: number
  ): Observable<ChatMessage> {
    const body: Record<string, unknown> = { content };
    if (replyToId !== undefined) body['reply_to_id'] = replyToId;
    return this.http.post<ChatMessage>(
      `${this.apiUrl}/conversations/${conversationId}/messages`,
      body,
      // Not blocking: the screen would freeze on every message and the next
      // one could not be typed. The chat shows its own sending state.
      { context: new HttpContext().set(BACKGROUND_REQUEST, true) }
    );
  }

  sendFileMessage(conversationId: number, file: File, replyToId?: number): Observable<ChatMessage> {
    const formData = new FormData();
    formData.append('file', file);
    const params: Record<string, string> = {};
    if (replyToId !== undefined) params['reply_to_id'] = replyToId.toString();
    return this.http.post<ChatMessage>(
      `${this.apiUrl}/conversations/${conversationId}/messages/files`,
      formData,
      { params }
    );
  }

  deleteMessage(messageId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/messages/${messageId}`);
  }

  // ── Members ────────────────────────────────────────────────────────

  getMembers(conversationId: number): Observable<ChatMember[]> {
    return this.http.get<ChatMember[]>(
      `${this.apiUrl}/conversations/${conversationId}/members`
    );
  }

  addMember(conversationId: number, userId: number): Observable<ChatMember> {
    return this.http.post<ChatMember>(
      `${this.apiUrl}/conversations/${conversationId}/members`,
      { target_user_id: userId }
    );
  }

  leaveGroup(conversationId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/conversations/${conversationId}/leave`
    );
  }

  removeMember(conversationId: number, userId: number): Observable<void> {
    return this.http.delete<void>(
      `${this.apiUrl}/conversations/${conversationId}/members/${userId}`
    );
  }

  updateMemberRole(
    conversationId: number,
    userId: number,
    role: 'admin' | 'member'
  ): Observable<ChatMember> {
    return this.http.put<ChatMember>(
      `${this.apiUrl}/conversations/${conversationId}/members/${userId}/role`,
      { role }
    );
  }

  // ── Join Requests ──────────────────────────────────────────────────

  getJoinRequests(conversationId: number): Observable<JoinRequest[]> {
    return this.http.get<JoinRequest[]>(
      `${this.apiUrl}/conversations/${conversationId}/join-requests`
    );
  }

  sendJoinRequest(conversationId: number): Observable<JoinRequest> {
    return this.http.post<JoinRequest>(
      `${this.apiUrl}/conversations/${conversationId}/join-requests`,
      {}
    );
  }

  reviewJoinRequest(
    conversationId: number,
    requestId: number,
    status: 'accepted' | 'rejected'
  ): Observable<JoinRequest> {
    return this.http.put<JoinRequest>(
      `${this.apiUrl}/conversations/${conversationId}/join-requests/${requestId}`,
      { status }
    );
  }

  // ── User search ────────────────────────────────────────────────────

  searchUsers(query: string, entityId?: number | null): Observable<UserSearchResult[]> {
    const params: Record<string, string> = { q: query };
    if (entityId != null) {
      params['entity_id'] = entityId.toString();
    }
    return this.http.get<UserSearchResult[]>(`${this.apiUrl}/users/search`, { params });
  }

  // ── Helpers ────────────────────────────────────────────────────────

  markConversationRead(conversationId: number): void {
    this.conversations.update((list) =>
      list.map((c) => {
        if (c.id !== conversationId) return c;
        const prev = c.unread_count;
        this.totalUnread.update((n) => Math.max(0, n - prev));
        return { ...c, unread_count: 0 };
      })
    );
  }

  updateConversationMutedPinned(
    conversationId: number,
    changes: { is_muted?: boolean; is_pinned?: boolean }
  ): void {
    this.conversations.update((list) => {
      const updated = list.map((c) =>
        c.id === conversationId ? { ...c, ...changes } : c
      );
      return [...updated].sort((a, b) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return 0;
      });
    });
  }

  upsertConversationInList(conv: ConversationListItem): void {
    this.conversations.update((list) => {
      const idx = list.findIndex((c) => c.id === conv.id);
      let updated: ConversationListItem[];
      if (idx >= 0) {
        updated = [...list];
        updated[idx] = conv;
      } else {
        updated = [conv, ...list];
      }
      return [...updated].sort((a, b) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return 0;
      });
    });
  }
}
