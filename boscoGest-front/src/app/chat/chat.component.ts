import { Component, OnInit, OnDestroy, signal, computed, inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { ChatService } from './chat.service';
import { ConversationListComponent } from './conversation-list/conversation-list.component';
import { ConversationViewComponent } from './conversation-view/conversation-view.component';
import { ConversationListItem } from '../models/chat.model';

@Component({
  selector: 'app-chat',
  imports: [
    CommonModule,
    MatIconModule,
    ConversationListComponent,
    ConversationViewComponent,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChatComponent implements OnInit, OnDestroy {
  private chatService = inject(ChatService);

  selectedConversationId = signal<number | null>(null);
  showMobileView = signal<'list' | 'chat'>('list');

  conversations = this.chatService.conversations;

  selectedConversation = computed((): ConversationListItem | null => {
    const id = this.selectedConversationId();
    if (!id) return null;
    return this.conversations().find((c) => c.id === id) ?? null;
  });

  ngOnInit(): void {
    this.chatService.connect();
    this.chatService.loadConversations();

    const pending = this.chatService.pendingConversationId();
    if (pending !== null) {
      this.chatService.pendingConversationId.set(null);
      this.selectedConversationId.set(pending);
      this.showMobileView.set('chat');
    }
  }

  ngOnDestroy(): void {
    this.chatService.onMessage = null;
  }

  onSelectConversation(conv: ConversationListItem): void {
    this.selectedConversationId.set(conv.id);
    this.chatService.markConversationRead(conv.id);
    this.showMobileView.set('chat');
  }

  onBackToList(): void {
    this.showMobileView.set('list');
    this.selectedConversationId.set(null);
  }

  onConversationCreated(conv: ConversationListItem): void {
    this.chatService.upsertConversationInList(conv);
    this.selectedConversationId.set(conv.id);
    this.showMobileView.set('chat');
  }
}
