import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { UsersService } from '../users.service';
import { EntitiesService } from '../../entities/entities.service';
import { ChatService } from '../../chat/chat.service';
import { EntityResponse } from '../../models/user.model';

interface DirectoryMember {
  id: number;
  name: string;
  surname: string;
}

@Component({
  selector: 'app-member-directory',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatCardModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatIconModule, MatButtonModule,
    MatPaginatorModule, MatProgressSpinnerModule, MatSnackBarModule
  ],
  templateUrl: './member-directory.component.html',
  styleUrl: './member-directory.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MemberDirectoryComponent implements OnInit {
  private destroyRef = inject(DestroyRef);
  private usersService = inject(UsersService);
  private entitiesService = inject(EntitiesService);
  private chatService = inject(ChatService);
  private router = inject(Router);
  private snackBar = inject(MatSnackBar);
  private requests$ = new Subject<{
    skip: number; limit: number; search: string; associationId: number | null
  }>();
  private search$ = new Subject<string>();

  members = signal<DirectoryMember[]>([]);
  associations = signal<EntityResponse[]>([]);
  selectedAssociation = signal<number | null>(null);
  searchTerm = signal('');
  total = signal(0);
  pageSize = signal(25);
  pageIndex = signal(0);
  loading = signal(true);
  contactingId = signal<number | null>(null);

  ngOnInit(): void {
    this.requests$.pipe(
      switchMap(request => this.usersService.getMemberDirectory(
        request.skip, request.limit, request.search, request.associationId
      ).pipe(
        catchError(() => {
          this.loading.set(false);
          this.snackBar.open('No se pudo cargar el directorio', 'Cerrar', { duration: 4000 });
          return EMPTY;
        })
      )),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(page => {
      this.members.set(page.items);
      this.total.set(page.total);
      this.loading.set(false);
    });

    this.search$.pipe(
      debounceTime(300), distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(term => {
      this.searchTerm.set(term);
      this.pageIndex.set(0);
      this.load();
    });

    this.entitiesService.getLocalAssociations()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: entities => this.associations.set(entities),
        error: () => this.snackBar.open(
          'No se pudo cargar la lista de asociaciones', 'Cerrar', { duration: 4000 }
        )
      });

    this.load();
  }

  onSearch(term: string): void { this.search$.next(term); }

  onAssociationChange(id: number | null): void {
    this.selectedAssociation.set(id);
    this.pageIndex.set(0);
    this.load();
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.requests$.next({
      skip: this.pageIndex() * this.pageSize(),
      limit: this.pageSize(),
      search: this.searchTerm(),
      associationId: this.selectedAssociation()
    });
  }

  contact(member: DirectoryMember): void {
    if (this.contactingId() !== null) return;
    this.contactingId.set(member.id);
    this.chatService.getOrCreateDirect(member.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: conversation => {
          this.contactingId.set(null);
          this.chatService.upsertConversationInList(conversation);
          this.chatService.pendingConversationId.set(conversation.id);
          this.router.navigate(['/chat']);
        },
        error: () => {
          this.contactingId.set(null);
          this.snackBar.open('No se pudo abrir la conversación', 'Cerrar', { duration: 4000 });
        }
      });
  }
}
