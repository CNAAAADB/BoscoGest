import { Component, OnInit, signal, computed, ChangeDetectionStrategy} from '@angular/core';
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
import {
  ChangeRoleDialogComponent,
  ChangeRoleDialogData,
} from '../change-role-dialog/change-role-dialog.component';
import { AuthService } from '../../auth/auth.service';
import { BoardPositionsComponent } from '../board-positions/board-positions.component';

interface EntityMembership {
  membershipId: number;
  entityId: number;
  entityName: string;
  roleName: string;
  isActive: boolean;
  /** Si quien mira puede cambiar el rol en esa asociación concreta. */
  canChangeRole: boolean;
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
    MatTooltipModule,
    BoardPositionsComponent
  ],
  templateUrl: './user-detail.component.html',
  styleUrl: './user-detail.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UserDetailComponent implements OnInit {
  user = signal<UserDetails | null>(null);

  /**
   * A sign-in link to hand over in person, for members the welcome email did
   * not reach. Held only in this screen — it is never fetched again, so
   * leaving the page loses it, which is the right default for a credential.
   */
  activationLink = signal<string | null>(null);
  activationLinkHours = signal<number>(72);
  issuingLink = signal(false);
  loading = signal<boolean>(true);
  userId: number | null = null;

  // Check if viewing own profile
  isOwnProfile = computed(() => {
    const currentUser = this.authService.getCurrentUser();
    const viewedUser = this.user();
    return currentUser && viewedUser && currentUser.id === viewedUser.id;
  });

  /**
   * Sensitive fields are redacted to null by the backend for viewers without
   * users:read_sensitive. Hiding the rows is more honest than rendering them
   * blank, which reads as "not provided" — a different claim entirely.
   *
   * A user always sees their own record in full.
   */
  canSeeSensitive = computed(() =>
    this.isOwnProfile() || this.authService.hasPermission('users', 'read_sensitive')
  );

  // Display columns
  displayedColumns: string[] = [
    'entityId',
    'entityName',
    'roleName',
    'isActive',
    'actions',
  ];

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
        isActive: m.is_active,
        // Por asociación, no global: memberships:update no se hereda, así que
        // tenerlo en una no da derecho sobre las demás.
        canChangeRole: this.authService.hasPermissionAtEntity(
          m.entity!.id, 'memberships', 'update'
        )
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

  /**
   * Cambia el rol de esta persona en una asociación.
   *
   * Aceptar una solicitud de alta crea siempre la membresía como `socio`, así
   * que sin esto no había forma de nombrar a nadie administrador.
   */
  openChangeRoleDialog(membership: EntityMembership): void {
    const user = this.user();
    if (!user || !membership.canChangeRole) return;

    const data: ChangeRoleDialogData = {
      membershipId: membership.membershipId,
      entityId: membership.entityId,
      entityName: membership.entityName,
      currentRoleName: membership.roleName,
      userName: `${user.name} ${user.surname}`,
    };

    this.dialog
      .open(ChangeRoleDialogComponent, { width: '420px', data })
      .afterClosed()
      .subscribe((changed) => {
        if (!changed) return;
        this.snackBar.open('Rol actualizado', 'Cerrar', { duration: 3000 });
        // Se recarga en vez de tocar la señal a mano: la tabla se alimenta del
        // usuario, y así el rol mostrado viene del servidor y no de lo que
        // creemos haber guardado.
        if (this.userId) this.loadUser(this.userId);
      });
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

  getActivationLink(): void {
    const target = this.user();
    if (!target || this.issuingLink()) {
      return;
    }

    this.issuingLink.set(true);
    this.usersService.issueActivationLink(target.id).subscribe({
      next: ({ url, expires_in_hours }) => {
        this.issuingLink.set(false);
        this.activationLink.set(url);
        this.activationLinkHours.set(expires_in_hours);
      },
      error: (error) => {
        this.issuingLink.set(false);
        this.snackBar.open(
          error?.error?.detail || 'No se ha podido generar el enlace',
          'Cerrar',
          { duration: 6000, panelClass: 'error-snackbar' }
        );
      },
    });
  }

  copyActivationLink(): void {
    const url = this.activationLink();
    if (!url) {
      return;
    }
    navigator.clipboard.writeText(url).then(
      () =>
        this.snackBar.open('Enlace copiado', 'Cerrar', {
          duration: 2500,
          panelClass: 'success-snackbar',
        }),
      () =>
        // Clipboard access can be refused; the link is on screen either way.
        this.snackBar.open(
          'No se ha podido copiar. Selecciona el enlace y cópialo a mano.',
          'Cerrar',
          { duration: 5000 }
        )
    );
  }
}
