import { Component, DestroyRef, OnInit, computed, inject, signal, ChangeDetectionStrategy} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { MatTableModule } from '@angular/material/table';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { UsersService } from '../users.service';
import { PaginatedUsers, UserResponse } from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { AuthService } from '../../auth/auth.service';
import { ChatService } from '../../chat/chat.service';
import { memberReviewReasons } from './member-review.utils';

@Component({
  selector: 'app-users-list',
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatFormFieldModule,
    MatInputModule,
    MatPaginatorModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTooltipModule
  ],
  templateUrl: './users-list.component.html',
  styleUrl: './users-list.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UsersListComponent implements OnInit {
  private destroyRef = inject(DestroyRef);

  users = signal<UserResponse[]>([]);
  /** Full server-side count, which is usually far larger than the loaded page. */
  total = signal<number>(0);
  pageIndex = signal<number>(0);
  pageSize = signal<number>(25);
  searchTerm = signal<string>('');
  reviewOnly = signal<boolean>(false);

  /** Only true for the very first load: a spinner on every keystroke flickers. */
  loading = signal<boolean>(true);
  /** Subtler indicator while a search or page change is in flight. */
  refreshing = signal<boolean>(false);

  private searchInput$ = new Subject<string>();
  /** All page and search requests pass through this stream so older HTTP calls are cancelled. */
  private pageRequests$ = new Subject<{ skip: number; limit: number; search: string; reviewOnly: boolean }>();

  /**
   * DNI is hidden entirely from viewers without users:read_sensitive — the
   * backend redacts it to null for them, so the column would only ever show
   * blanks and invite the reader to think the data is missing.
   */
  canSeeSensitive = computed(() =>
    this.authService.hasPermission('users', 'read_sensitive')
  );

  canSeeContact = computed(() =>
    this.authService.hasPermission('users', 'read')
  );

  /** Display warnings only to someone who may actually correct a record. */
  canReviewData = computed(() =>
    this.authService.hasPermission('users', 'update')
  );

  reviewReasons(user: UserResponse): string[] {
    if (!this.canReviewData()) return [];
    return memberReviewReasons(user, {
      canReadContact: this.canSeeContact(),
      canReadSensitive: this.canSeeSensitive(),
    });
  }

  displayedColumns = computed(() => {
    const columns = ['id', 'name', 'email'];
    if (this.canSeeSensitive()) {
      columns.push('dni');
    }
    return [...columns, 'is_active', 'actions'];
  });

  // Check if user can create users
  canCreateUsers = computed(() => {
    return this.authService.hasPermission('users', 'create');
  });

  // Check if user can edit users
  canEditUsers = computed(() => {
    return this.authService.hasPermission('users', 'update');
  });

  // Check if user can delete users
  canDeleteUsers = computed(() => {
    return this.authService.hasPermission('users', 'delete');
  });

  // Check if user can create memberships
  canCreateMemberships = computed(() => {
    return this.authService.hasPermission('memberships', 'create');
  });

  constructor(
    private usersService: UsersService,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private authService: AuthService,
    private chatService: ChatService
  ) {}

  ngOnInit(): void {
    // One request pipeline handles initial load, page changes, search and
    // post-deletion refreshes. switchMap cancels stale HTTP requests.
    this.pageRequests$
      .pipe(
        switchMap(({ skip, limit, search, reviewOnly }) =>
          this.usersService.getManagedUsers(skip, limit, search, reviewOnly).pipe(
            catchError((error) => {
              this.reportLoadError(error);
              return EMPTY;
            })
          )
        ),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((page) => this.applyPage(page));

    this.searchInput$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((term) => {
        this.pageIndex.set(0);
        this.searchTerm.set(term);
        this.loadUsers();
      });

    this.loadUsers();
  }

  onSearchInput(term: string): void {
    this.searchInput$.next(term);
  }

  clearSearch(): void {
    this.searchInput$.next('');
  }

  toggleReviewOnly(checked: boolean): void {
    this.reviewOnly.set(checked);
    this.pageIndex.set(0);
    this.loadUsers();
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex.set(event.pageIndex);
    this.pageSize.set(event.pageSize);
    this.loadUsers();
  }

  loadUsers(): void {
    this.refreshing.set(true);
    const skip = this.pageIndex() * this.pageSize();

    this.pageRequests$.next({
      skip,
      limit: this.pageSize(),
      search: this.searchTerm(),
      reviewOnly: this.reviewOnly()
    });
  }

  private applyPage(page: PaginatedUsers): void {
    this.users.set(page.items);
    this.total.set(page.total);
    this.loading.set(false);
    this.refreshing.set(false);
  }

  private reportLoadError(error: unknown): void {
    console.error('Error loading users:', error);
    this.snackBar.open('Error al cargar los usuarios', 'Cerrar', {
      duration: 3000,
      panelClass: 'error-snackbar'
    });
    this.loading.set(false);
    this.refreshing.set(false);
  }

  createUser(): void {
    this.router.navigate(['/users/new']);
  }

  viewUser(user: UserResponse): void {
    this.router.navigate(['/users', user.id]);
  }

  editUser(user: UserResponse): void {
    this.router.navigate(['/users', user.id, 'edit']);
  }

  createMembership(user: UserResponse): void {
    this.router.navigate(['/users', user.id, 'create-membership']);
  }

  openChat(user: UserResponse): void {
    this.chatService.getOrCreateDirect(user.id).subscribe({
      next: (conv) => {
        this.chatService.upsertConversationInList(conv);
        this.chatService.pendingConversationId.set(conv.id);
        this.router.navigate(['/chat']);
      },
      error: () => {
        this.snackBar.open('Error al abrir el chat', 'Cerrar', { duration: 3000 });
      },
    });
  }

  isCurrentUser(user: UserResponse): boolean {
    const currentUser = this.authService.getCurrentUser();
    return currentUser?.id === user.id;
  }

  deleteUser(user: UserResponse): void {
    // Prevent user from deleting themselves
    const currentUser = this.authService.getCurrentUser();
    if (currentUser && currentUser.id === user.id) {
      this.snackBar.open('No puedes eliminar tu propio usuario', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      return;
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Confirmar eliminación',
        message: `¿Está seguro de que desea eliminar al usuario "${user.name} ${user.surname}"? Esta acción no se puede deshacer.`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.usersService.deleteUser(user.id).subscribe({
          next: () => {
            this.snackBar.open('Usuario eliminado correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.loadUsers();
          },
          error: (error) => {
            console.error('Error deleting user:', error);
            this.snackBar.open('Error al eliminar el usuario', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }
}
