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
import { RolesService } from '../roles.service';
import { RoleDetails } from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';

interface GroupedPermission {
  resource: string;
  actions: string[];
  description: string | null;
}

@Component({
  selector: 'app-role-detail',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatDividerModule,
    MatTableModule
  ],
  templateUrl: './role-detail.component.html',
  styleUrl: './role-detail.component.css'
})
export class RoleDetailComponent implements OnInit {
  role = signal<RoleDetails | null>(null);
  loading = signal<boolean>(true);
  roleId: number | null = null;
  displayedColumns: string[] = ['resource', 'actions', 'description'];

  groupedPermissions = computed<GroupedPermission[]>(() => {
    const currentRole = this.role();
    if (!currentRole?.permissions) return [];

    const grouped = new Map<string, GroupedPermission>();

    currentRole.permissions.forEach(permission => {
      if (grouped.has(permission.resource)) {
        grouped.get(permission.resource)!.actions.push(permission.action);
      } else {
        grouped.set(permission.resource, {
          resource: permission.resource,
          actions: [permission.action],
          description: permission.description
        });
      }
    });

    return Array.from(grouped.values());
  });

  constructor(
    private rolesService: RolesService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.roleId = parseInt(id, 10);
      this.loadRole(this.roleId);
    } else {
      this.router.navigate(['/roles']);
    }
  }

  loadRole(id: number): void {
    this.loading.set(true);
    this.rolesService.getRole(id).subscribe({
      next: (role) => {
        this.role.set(role);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading role:', error);
        this.snackBar.open('Error al cargar el rol', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/roles']);
      }
    });
  }

  editRole(): void {
    if (this.roleId) {
      this.router.navigate(['/roles', this.roleId, 'edit']);
    }
  }

  deleteRole(): void {
    const roleData = this.role();
    if (!roleData || !this.roleId) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Confirmar eliminación',
        message: `¿Está seguro de que desea eliminar el rol "${roleData.name}"? Esta acción no se puede deshacer.`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.rolesService.deleteRole(this.roleId!).subscribe({
          next: () => {
            this.snackBar.open('Rol eliminado correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.router.navigate(['/roles']);
          },
          error: (error) => {
            console.error('Error deleting role:', error);
            this.snackBar.open('Error al eliminar el rol', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/roles']);
  }
}
