import {
  Component,
  signal,
  computed,
  OnInit, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';

import { ChatService } from '../chat.service';
import { EntitiesService } from '../../entities/entities.service';
import { ConversationListItem, UserSearchResult } from '../../models/chat.model';
import { EntityResponse } from '../../models/user.model';

@Component({
  selector: 'app-new-conversation-dialog',
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './new-conversation-dialog.component.html',
  styleUrl: './new-conversation-dialog.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NewConversationDialogComponent implements OnInit {
  // Direct chat tab
  searchQuery = signal('');
  searchResults = signal<UserSearchResult[]>([]);
  searchLoading = signal(false);
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  // Association filter
  entities = signal<EntityResponse[]>([]);
  selectedEntityId = signal<number | null>(null);

  // Group tab
  groupName = signal('');
  groupDescription = signal('');
  creating = signal(false);

  constructor(
    private dialogRef: MatDialogRef<NewConversationDialogComponent>,
    private chatService: ChatService,
    private snackBar: MatSnackBar,
    private entitiesService: EntitiesService
  ) {}

  ngOnInit(): void {
    this.entitiesService.getLocalAssociations()
      .subscribe({
        next: (entities) => this.entities.set(entities),
        error: () => this.entities.set([]),
      });
  }

  onEntityFilterChange(entityId: number | null): void {
    this.selectedEntityId.set(entityId);
    // Re-run the current search with the new filter, if any query is active.
    if (this.searchQuery().trim().length >= 2) {
      this.runSearch(this.searchQuery().trim());
    }
  }

  onSearchInput(value: string): void {
    this.searchQuery.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    if (value.trim().length < 2) {
      this.searchResults.set([]);
      return;
    }
    this.searchLoading.set(true);
    this.searchTimer = setTimeout(() => this.runSearch(value.trim()), 300);
  }

  private runSearch(query: string): void {
    this.searchLoading.set(true);
    this.chatService.searchUsers(query, this.selectedEntityId()).subscribe({
      next: (users) => {
        this.searchResults.set(users);
        this.searchLoading.set(false);
      },
      error: () => this.searchLoading.set(false),
    });
  }

  startDirectChat(user: UserSearchResult): void {
    this.chatService.getOrCreateDirect(user.id).subscribe({
      next: (conv) => this.dialogRef.close(conv),
      error: () =>
        this.snackBar.open('Error al iniciar la conversación', 'Cerrar', {
          duration: 3000,
        }),
    });
  }

  createGroup(): void {
    const name = this.groupName().trim();
    if (!name) return;

    this.creating.set(true);
    this.chatService
      .createGroup(name, this.groupDescription().trim() || undefined)
      .subscribe({
        next: (conv) => {
          this.creating.set(false);
          this.dialogRef.close(conv);
        },
        error: () => {
          this.creating.set(false);
          this.snackBar.open('Error al crear el grupo', 'Cerrar', {
            duration: 3000,
          });
        },
      });
  }

  cancel(): void {
    this.dialogRef.close();
  }
}
