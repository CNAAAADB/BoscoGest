import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DestroyRef } from '@angular/core';
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
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
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

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {
      const id = Number(params.get('conversation'));
      if (Number.isSafeInteger(id) && id > 0) {
        this.selectedConversationId.set(id);
        this.showMobileView.set('chat');
      }
    });
    const pending = this.chatService.pendingConversationId();
    if (pending !== null) {
      this.chatService.pendingConversationId.set(null);
      if (this.route.snapshot.queryParamMap.has('conversation')) return;
      this.selectedConversationId.set(pending);
      this.showMobileView.set('chat');
    }
  }

  ngOnDestroy(): void {
    this.chatService.onMessage = null;
  }

  onSelectConversation(conv: ConversationListItem): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: { conversation: conv.id }, replaceUrl: true });
    this.selectedConversationId.set(conv.id);
    this.chatService.markConversationRead(conv.id);
    this.showMobileView.set('chat');
  }

  onBackToList(): void {
    void this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    this.showMobileView.set('list');
    this.selectedConversationId.set(null);
  }

  onConversationCreated(conv: ConversationListItem): void {
    this.chatService.upsertConversationInList(conv);
    void this.router.navigate([], { relativeTo: this.route, queryParams: { conversation: conv.id }, replaceUrl: true });
    this.selectedConversationId.set(conv.id);
    this.showMobileView.set('chat');
  }
}
