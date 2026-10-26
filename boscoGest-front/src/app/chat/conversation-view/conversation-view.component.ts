import {
  Component,
  input,
  output,
  signal,
  computed,
  OnInit,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
  ElementRef,
  AfterViewChecked,
  inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ChatService } from '../chat.service';
import { AuthService } from '../../auth/auth.service';
import { GroupSettingsDialogComponent } from '../group-settings-dialog/group-settings-dialog.component';
import {
  ChatMessage,
  ChatUserBrief,
  ChatWsPayload,
  ConversationListItem,
} from '../../models/chat.model';

@Component({
  selector: 'app-conversation-view',
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
  ],
  templateUrl: './conversation-view.component.html',
  styleUrl: './conversation-view.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConversationViewComponent
  implements OnInit, OnChanges, OnDestroy, AfterViewChecked
{
  conversationId = input.required<number>();
  conversation = input<ConversationListItem | null>(null);
  back = output<void>();

  @ViewChild('messagesEnd') messagesEnd!: ElementRef;
  @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;

  private authService = inject(AuthService);
  private chatService = inject(ChatService);
  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);

  messages = signal<ChatMessage[]>([]);
  loading = signal(true);
  sending = signal(false);
  newMessage = signal('');
  hasMore = signal(true);
  loadingMore = signal(false);

  // Reply
  replyTo = signal<ChatMessage | null>(null);

  // Typing indicator
  typingUsers = signal<ChatUserBrief[]>([]);
  private typingTimers = new Map<number, ReturnType<typeof setTimeout>>();
  private typingDebounce: ReturnType<typeof setTimeout> | null = null;

  // Search
  searchMode = signal(false);
  searchQuery = signal('');
  searchResults = signal<ChatMessage[]>([]);
  searchLoading = signal(false);

  // File upload
  uploadingFile = signal(false);

  currentUserId = this.authService.getCurrentUser()?.id ?? 0;

  private shouldScrollToBottom = false;

  typingText = computed(() => {
    const users = this.typingUsers();
    if (users.length === 0) return '';
    if (users.length === 1) return `${users[0].name} está escribiendo…`;
    if (users.length === 2)
      return `${users[0].name} y ${users[1].name} están escribiendo…`;
    return 'Varios están escribiendo…';
  });

  ngOnInit(): void {
    this.loadMessages();
    this.chatService.onMessage = (payload) => this.handleWsPayload(payload);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['conversationId'] && !changes['conversationId'].firstChange) {
      this.messages.set([]);
      this.hasMore.set(true);
      this.replyTo.set(null);
      this.typingUsers.set([]);
      this.searchMode.set(false);
      this.searchQuery.set('');
      this.searchResults.set([]);
      this.loadMessages();
    }
  }

  ngOnDestroy(): void {
    this.chatService.onMessage = null;
    this.typingTimers.forEach((t) => clearTimeout(t));
    if (this.typingDebounce) clearTimeout(this.typingDebounce);
  }

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
      this.shouldScrollToBottom = false;
    }
  }

  private loadMessages(): void {
    this.loading.set(true);
    this.chatService.getMessages(this.conversationId()).subscribe({
      next: (msgs) => {
        this.messages.set(msgs);
        this.hasMore.set(msgs.length === 50);
        this.shouldScrollToBottom = true;
        this.loading.set(false);
        this.chatService.markConversationRead(this.conversationId());
      },
      error: () => this.loading.set(false),
    });
  }

  loadMoreMessages(): void {
    const first = this.messages()[0];
    if (!first || this.loadingMore()) return;

    this.loadingMore.set(true);
    this.chatService
      .getMessages(this.conversationId(), first.id)
      .subscribe({
        next: (older) => {
          this.messages.update((list) => [...older, ...list]);
          this.hasMore.set(older.length === 50);
          this.loadingMore.set(false);
        },
        error: () => this.loadingMore.set(false),
      });
  }

  sendMessage(): void {
    const content = this.newMessage().trim();
    if (!content || this.sending()) return;

    this.sending.set(true);
    const replyId = this.replyTo()?.id;

    this.chatService.sendMessage(this.conversationId(), content, replyId).subscribe({
      next: (msg) => {
        this.newMessage.set('');
        this.replyTo.set(null);
        this.messages.update((list) => [...list, msg]);
        this.shouldScrollToBottom = true;
        this.sending.set(false);
      },
      error: () => {
        this.snackBar.open('Error al enviar el mensaje', 'Cerrar', { duration: 3000 });
        this.sending.set(false);
      },
    });
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
    // Send typing indicator (debounced)
    this.sendTypingIndicator();
  }

  onInput(): void {
    this.sendTypingIndicator();
  }

  private sendTypingIndicator(): void {
    if (this.typingDebounce) clearTimeout(this.typingDebounce);
    this.typingDebounce = setTimeout(() => {
      this.chatService.sendTyping(this.conversationId());
    }, 300);
  }

  // ── Reply ──────────────────────────────────────────────────────────

  startReply(msg: ChatMessage): void {
    this.replyTo.set(msg);
  }

  cancelReply(): void {
    this.replyTo.set(null);
  }

  // ── Delete ─────────────────────────────────────────────────────────

  deleteMessage(msg: ChatMessage): void {
    this.chatService.deleteMessage(msg.id).subscribe({
      next: () => {
        this.messages.update((list) =>
          list.map((m) =>
            m.id === msg.id ? { ...m, is_deleted: true, content: '' } : m
          )
        );
      },
      error: () =>
        this.snackBar.open('Error al eliminar el mensaje', 'Cerrar', {
          duration: 3000,
        }),
    });
  }

  // ── File upload ────────────────────────────────────────────────────

  openFileChooser(): void {
    this.fileInput?.nativeElement.click();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    input.value = ''; // reset so same file can be re-selected

    if (file.size > 20 * 1024 * 1024) {
      this.snackBar.open('El archivo supera el límite de 20 MB', 'Cerrar', { duration: 3000 });
      return;
    }

    this.uploadingFile.set(true);
    const replyId = this.replyTo()?.id;
    this.chatService.sendFileMessage(this.conversationId(), file, replyId).subscribe({
      next: (msg) => {
        this.replyTo.set(null);
        this.messages.update((list) => [...list, msg]);
        this.shouldScrollToBottom = true;
        this.uploadingFile.set(false);
      },
      error: () => {
        this.snackBar.open('Error al enviar el archivo', 'Cerrar', { duration: 3000 });
        this.uploadingFile.set(false);
      },
    });
  }

  // ── Search ─────────────────────────────────────────────────────────

  toggleSearch(): void {
    this.searchMode.update((v) => !v);
    if (!this.searchMode()) {
      this.searchQuery.set('');
      this.searchResults.set([]);
    }
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value);
    if (value.trim().length < 2) {
      this.searchResults.set([]);
      return;
    }
    this.searchLoading.set(true);
    this.chatService.searchMessages(this.conversationId(), value.trim()).subscribe({
      next: (results) => {
        this.searchResults.set(results);
        this.searchLoading.set(false);
      },
      error: () => this.searchLoading.set(false),
    });
  }

  // ── Group settings ─────────────────────────────────────────────────

  openGroupSettings(): void {
    const conv = this.conversation();
    if (!conv) return;
    this.dialog.open(GroupSettingsDialogComponent, {
      width: '520px',
      data: { conversationId: this.conversationId(), conversation: conv },
    });
  }

  // ── WS payload handler ─────────────────────────────────────────────

  private handleWsPayload(payload: ChatWsPayload): void {
    if (payload.conversation_id !== this.conversationId()) return;

    if (payload.type === 'new_message') {
      const exists = this.messages().some((m) => m.id === payload.message.id);
      if (!exists) {
        this.messages.update((list) => [...list, payload.message]);
        this.shouldScrollToBottom = true;
        this.chatService.markConversationRead(this.conversationId());
      }
      // Clear typing for the sender
      if (payload.message.sender_id) {
        this.clearTyping(payload.message.sender_id);
      }
    } else if (payload.type === 'message_deleted') {
      this.messages.update((list) =>
        list.map((m) =>
          m.id === payload.message_id
            ? { ...m, is_deleted: true, content: '' }
            : m
        )
      );
    } else if (payload.type === 'typing') {
      this.showTyping(payload.user);
    }
  }

  private showTyping(user: ChatUserBrief): void {
    if (user.id === this.currentUserId) return;
    this.typingUsers.update((list) => {
      if (!list.find((u) => u.id === user.id)) return [...list, user];
      return list;
    });
    // Auto-clear after 3 seconds
    const prev = this.typingTimers.get(user.id);
    if (prev) clearTimeout(prev);
    const t = setTimeout(() => this.clearTyping(user.id), 3000);
    this.typingTimers.set(user.id, t);
  }

  private clearTyping(userId: number): void {
    this.typingUsers.update((list) => list.filter((u) => u.id !== userId));
    const t = this.typingTimers.get(userId);
    if (t) {
      clearTimeout(t);
      this.typingTimers.delete(userId);
    }
  }

  // ── Display helpers ────────────────────────────────────────────────

  getConversationTitle(): string {
    const conv = this.conversation();
    if (!conv) return '';
    if (conv.type === 'direct' && conv.other_user) {
      return `${conv.other_user.name} ${conv.other_user.surname}`;
    }
    return conv.name || 'Grupo';
  }

  isOwn(msg: ChatMessage): boolean {
    return msg.sender_id === this.currentUserId;
  }

  isImage(msg: ChatMessage): boolean {
    return !!msg.file_type && msg.file_type.startsWith('image/');
  }

  formatTime(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return 'Hoy';
    if (date.toDateString() === yesterday.toDateString()) return 'Ayer';
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
  }

  isDifferentDay(current: ChatMessage, previous: ChatMessage | undefined): boolean {
    if (!previous) return true;
    return (
      new Date(current.created_at).toDateString() !==
      new Date(previous.created_at).toDateString()
    );
  }

  private scrollToBottom(): void {
    try {
      this.messagesEnd?.nativeElement?.scrollIntoView({ behavior: 'smooth' });
    } catch {}
  }
}
