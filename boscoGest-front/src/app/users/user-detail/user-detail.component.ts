import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTableModule } from '@angular/material/table';
import { MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { UsersService } from '../users.service';
import { UserDetails } from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { AuthService } from '../../auth/auth.service';

interface EntityMembership {
  membershipId: number;
  entityId: number;
  entityName: string;
  roleName: string;
  isActive: boolean;
}

@Component({
  selector: 'app-user-detail',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatDividerModule,
    MatTableModule,
    MatTooltipModule
  ],
  templateUrl: './user-detail.component.html',
  styleUrl: './user-detail.component.css'
})
export class UserDetailComponent implements OnInit {
  user = signal<UserDetails | null>(null);
  loading = signal<boolean>(true);
  userId: number | null = null;

  // Check if viewing own profile
  isOwnProfile = computed(() => {
    const currentUser = this.authService.getCurrentUser();
    const viewedUser = this.user();
    return currentUser && viewedUser && currentUser.id === viewedUser.id;
  });

  // Display columns
  displayedColumns: string[] = ['entityId', 'entityName', 'roleName', 'isActive'];

  // Get entity memberships with entity and role names
  entityMemberships = computed<EntityMembership[]>(() => {
    const currentUser = this.user();
    if (!currentUser?.memberships) return [];

    return currentUser.memberships
      .filter(m => m.entity && m.role)
      .map(m => ({
        membershipId: m.id,
        entityId: m.entity!.id,
        entityName: m.entity!.name,
        roleName: m.role!.name,
        isActive: m.is_active
      }));
  });

  constructor(
    private usersService: UsersService,
    private authService: AuthService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.userId = parseInt(id, 10);
      this.loadUser(this.userId);
    } else {
      this.snackBar.open('ID de usuario no válido', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      this.router.navigate(['/users']);
    }
  }

  loadUser(id: number): void {
    this.loading.set(true);

    this.usersService.getUserDetails(id).subscribe({
      next: (user) => {
        this.user.set(user);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading user:', error);
        this.snackBar.open('Error al cargar el usuario', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/users']);
      }
    });
  }

  editUser(): void {
    if (this.userId) {
      this.router.navigate(['/users', this.userId, 'edit']);
    }
  }

  deleteUser(): void {
    const currentUser = this.user();
    if (!currentUser) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Confirmar eliminación',
        message: `¿Está seguro de que desea eliminar al usuario "${currentUser.name} ${currentUser.surname}"? Esta acción no se puede deshacer.`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result && this.userId) {
        this.usersService.deleteUser(this.userId).subscribe({
          next: () => {
            this.snackBar.open('Usuario eliminado correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.router.navigate(['/users']);
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

  goBack(): void {
    this.router.navigate(['/users']);
  }
}
