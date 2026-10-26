import {
  Component,
  input,
  output,
  inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ConversationListItem } from '../../models/chat.model';
import { ChatService } from '../chat.service';
import { NewConversationDialogComponent } from '../new-conversation-dialog/new-conversation-dialog.component';

@Component({
  selector: 'app-conversation-list',
  imports: [CommonModule, MatIconModule, MatButtonModule, MatTooltipModule],
  templateUrl: './conversation-list.component.html',
  styleUrl: './conversation-list.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConversationListComponent {
  conversations = input.required<ConversationListItem[]>();
  selectedId = input<number | null>(null);

  selectConversation = output<ConversationListItem>();
  conversationCreated = output<ConversationListItem>();

  private dialog = inject(MatDialog);
  private snackBar = inject(MatSnackBar);
  private chatService = inject(ChatService);

  openNewConversation(): void {
    const ref = this.dialog.open(NewConversationDialogComponent, {
      width: '480px',
    });
    ref.afterClosed().subscribe((conv: ConversationListItem | undefined) => {
      if (conv) this.conversationCreated.emit(conv);
    });
  }

  select(conv: ConversationListItem): void {
    this.selectConversation.emit(conv);
  }

  toggleMute(event: MouseEvent, conv: ConversationListItem): void {
    event.stopPropagation();
    const action = conv.is_muted
      ? this.chatService.unmuteConversation(conv.id)
      : this.chatService.muteConversation(conv.id);

    action.subscribe({
      next: () => {
        this.chatService.updateConversationMutedPinned(conv.id, {
          is_muted: !conv.is_muted,
        });
      },
      error: () =>
        this.snackBar.open('Error al cambiar silencio', 'Cerrar', { duration: 2000 }),
    });
  }

  togglePin(event: MouseEvent, conv: ConversationListItem): void {
    event.stopPropagation();
    const action = conv.is_pinned
      ? this.chatService.unpinConversation(conv.id)
      : this.chatService.pinConversation(conv.id);

    action.subscribe({
      next: () => {
        this.chatService.updateConversationMutedPinned(conv.id, {
          is_pinned: !conv.is_pinned,
        });
      },
      error: () =>
        this.snackBar.open('Error al fijar conversación', 'Cerrar', { duration: 2000 }),
    });
  }

  getDisplayName(conv: ConversationListItem): string {
    if (conv.type === 'direct' && conv.other_user) {
      return `${conv.other_user.name} ${conv.other_user.surname}`;
    }
    return conv.name || 'Grupo';
  }

  getInitial(conv: ConversationListItem): string {
    return this.getDisplayName(conv).charAt(0).toUpperCase();
  }

  formatTime(dateStr: string | null | undefined): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'ahora';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
  }

  getLastMessagePreview(conv: ConversationListItem): string {
    if (!conv.last_message) return 'Sin mensajes aún';
    if (conv.last_message.is_deleted) return 'Mensaje eliminado';
    if (conv.last_message.message_type === 'file') return '📎 Archivo adjunto';
    if (conv.last_message.message_type === 'system') return conv.last_message.content;
    const content = conv.last_message.content;
    return content.length > 40 ? content.substring(0, 40) + '…' : content;
  }
}
