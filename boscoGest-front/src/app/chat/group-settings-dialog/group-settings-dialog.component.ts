import {
  Component,
  OnInit,
  signal,
  inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import { ChatService } from '../chat.service';
import { AuthService } from '../../auth/auth.service';
import {
  ChatMember,
  ConversationListItem,
  JoinRequest,
  UserSearchResult,
} from '../../models/chat.model';

export interface GroupSettingsData {
  conversationId: number;
  conversation: ConversationListItem;
}

@Component({
  selector: 'app-group-settings-dialog',
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatFormFieldModule,
    MatInputModule,
    MatMenuModule,
    MatTooltipModule,
  ],
  templateUrl: './group-settings-dialog.component.html',
  styleUrl: './group-settings-dialog.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class GroupSettingsDialogComponent implements OnInit {
  data = inject<GroupSettingsData>(MAT_DIALOG_DATA);
  private dialogRef = inject(MatDialogRef<GroupSettingsDialogComponent>);
  private chatService = inject(ChatService);
  private authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);

  members = signal<ChatMember[]>([]);
  joinRequests = signal<JoinRequest[]>([]);
  loading = signal(true);

  // Edit group info
  editName = signal('');
  editDescription = signal('');
  saving = signal(false);

  // Avatar upload
  uploadingAvatar = signal(false);

  // Add member search
  addSearchQuery = signal('');
  addSearchResults = signal<UserSearchResult[]>([]);
  addSearchLoading = signal(false);
  private addSearchTimer: ReturnType<typeof setTimeout> | null = null;

  isAdmin = this.data.conversation.my_role === 'admin';
  currentUserId = this.authService.getCurrentUser()?.id ?? 0;

  ngOnInit(): void {
    this.editName.set(this.data.conversation.name || '');
    this.loadMembers();
    if (this.isAdmin) this.loadJoinRequests();
  }

  loadMembers(): void {
    this.chatService.getMembers(this.data.conversationId).subscribe({
      next: (members) => {
        this.members.set(members);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  loadJoinRequests(): void {
    this.chatService.getJoinRequests(this.data.conversationId).subscribe({
      next: (reqs) => this.joinRequests.set(reqs),
    });
  }

  saveGroupInfo(): void {
    const name = this.editName().trim();
    if (!name) return;
    this.saving.set(true);
    this.chatService
      .updateGroup(this.data.conversationId, {
        name,
        description: this.editDescription().trim() || undefined,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.snackBar.open('Grupo actualizado', 'Cerrar', { duration: 2000 });
        },
        error: () => {
          this.saving.set(false);
          this.snackBar.open('Error al actualizar el grupo', 'Cerrar', {
            duration: 3000,
          });
        },
      });
  }

  promoteToAdmin(member: ChatMember): void {
    this.chatService
      .updateMemberRole(this.data.conversationId, member.user_id, 'admin')
      .subscribe({
        next: (updated) => {
          this.members.update((list) =>
            list.map((m) => (m.id === updated.id ? updated : m))
          );
          this.snackBar.open(`${member.user.name} ahora es administrador`, 'Cerrar', {
            duration: 2000,
          });
        },
      });
  }

  demoteToMember(member: ChatMember): void {
    this.chatService
      .updateMemberRole(this.data.conversationId, member.user_id, 'member')
      .subscribe({
        next: (updated) => {
          this.members.update((list) =>
            list.map((m) => (m.id === updated.id ? updated : m))
          );
        },
      });
  }

  removeMember(member: ChatMember): void {
    this.chatService
      .removeMember(this.data.conversationId, member.user_id)
      .subscribe({
        next: () => {
          this.members.update((list) => list.filter((m) => m.id !== member.id));
          this.snackBar.open(`${member.user.name} ha sido expulsado`, 'Cerrar', {
            duration: 2000,
          });
        },
        error: () =>
          this.snackBar.open('Error al expulsar al miembro', 'Cerrar', {
            duration: 3000,
          }),
      });
  }

  leaveGroup(): void {
    this.chatService.leaveGroup(this.data.conversationId).subscribe({
      next: () => {
        this.snackBar.open('Has abandonado el grupo', 'Cerrar', {
          duration: 2000,
        });
        this.dialogRef.close({ left: true });
      },
      error: () =>
        this.snackBar.open('Error al abandonar el grupo', 'Cerrar', {
          duration: 3000,
        }),
    });
  }

  onAddSearchInput(value: string): void {
    this.addSearchQuery.set(value);
    if (this.addSearchTimer) clearTimeout(this.addSearchTimer);
    if (value.trim().length < 2) {
      this.addSearchResults.set([]);
      return;
    }
    this.addSearchLoading.set(true);
    this.addSearchTimer = setTimeout(() => {
      this.chatService.searchUsers(value.trim()).subscribe({
        next: (users) => {
          const memberIds = new Set(this.members().map((m) => m.user_id));
          this.addSearchResults.set(users.filter((u) => !memberIds.has(u.id)));
          this.addSearchLoading.set(false);
        },
        error: () => this.addSearchLoading.set(false),
      });
    }, 300);
  }

  addMember(user: UserSearchResult): void {
    this.chatService.addMember(this.data.conversationId, user.id).subscribe({
      next: (member) => {
        this.members.update((list) => [...list, member]);
        this.addSearchQuery.set('');
        this.addSearchResults.set([]);
        this.snackBar.open(`${user.name} añadido al grupo`, 'Cerrar', {
          duration: 2000,
        });
      },
      error: () =>
        this.snackBar.open('Error al añadir al usuario', 'Cerrar', {
          duration: 3000,
        }),
    });
  }

  acceptRequest(req: JoinRequest): void {
    this.chatService
      .reviewJoinRequest(this.data.conversationId, req.id, 'accepted')
      .subscribe({
        next: () => {
          this.joinRequests.update((list) => list.filter((r) => r.id !== req.id));
          this.loadMembers();
          this.snackBar.open(`${req.user.name} añadido al grupo`, 'Cerrar', {
            duration: 2000,
          });
        },
      });
  }

  rejectRequest(req: JoinRequest): void {
    this.chatService
      .reviewJoinRequest(this.data.conversationId, req.id, 'rejected')
      .subscribe({
        next: () => {
          this.joinRequests.update((list) => list.filter((r) => r.id !== req.id));
        },
      });
  }

  isCurrentUser(member: ChatMember): boolean {
    return member.user_id === this.currentUserId;
  }

  onAvatarFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    input.value = '';

    if (!file.type.startsWith('image/')) {
      this.snackBar.open('Solo se permiten imágenes', 'Cerrar', { duration: 3000 });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.snackBar.open('La imagen supera el límite de 5 MB', 'Cerrar', { duration: 3000 });
      return;
    }

    this.uploadingAvatar.set(true);
    this.chatService.uploadGroupAvatar(this.data.conversationId, file).subscribe({
      next: () => {
        this.uploadingAvatar.set(false);
        this.snackBar.open('Avatar actualizado', 'Cerrar', { duration: 2000 });
      },
      error: () => {
        this.uploadingAvatar.set(false);
        this.snackBar.open('Error al subir el avatar', 'Cerrar', { duration: 3000 });
      },
    });
  }

  close(): void {
    this.dialogRef.close();
  }
}
