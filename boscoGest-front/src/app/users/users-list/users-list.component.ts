import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { UsersService } from '../users.service';
import { UserResponse } from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-users-list',
  imports: [
    CommonModule,
    MatTableModule,
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
})
export class UsersListComponent implements OnInit {
  users = signal<UserResponse[]>([]);
  loading = signal<boolean>(true);
  displayedColumns: string[] = ['id', 'name', 'email', 'dni', 'is_active', 'actions'];

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
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.loading.set(true);
    this.usersService.getManagedUsers().subscribe({
      next: (users) => {
        this.users.set(users);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading users:', error);
        this.snackBar.open('Error al cargar los usuarios', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
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
