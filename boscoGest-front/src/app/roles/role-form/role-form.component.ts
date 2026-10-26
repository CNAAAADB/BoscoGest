import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatListModule } from '@angular/material/list';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIconModule } from '@angular/material/icon';
import { RolesService } from '../roles.service';
import { AuthService } from '../../auth/auth.service';
import { PermissionsService } from '../../permissions/permissions.service';
import { RoleCreate, RoleUpdate, PermissionResponse, RoleDetails } from '../../models/user.model';

@Component({
  selector: 'app-role-form',
  imports: [
    MatTooltipModule,
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatListModule,
    MatIconModule
  ],
  templateUrl: './role-form.component.html',
  styleUrl: './role-form.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoleFormComponent implements OnInit {
  roleForm: FormGroup;
  loading = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  isSuperadmin = signal<boolean>(false);
  roleId: number | null = null;

  // Permissions management
  availablePermissions = signal<PermissionResponse[]>([]);
  selectedPermissions = signal<PermissionResponse[]>([]);

  /**
   * The association a new role will belong to — the one of the cargo in use.
   * Roles are per-association, so saying which one it is here saves finding
   * out afterwards that the role landed somewhere unexpected.
   */
  targetEntityName = signal<string>('');

  constructor(
    private fb: FormBuilder,
    private rolesService: RolesService,
    private permissionsService: PermissionsService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar,
    private authService: AuthService
  ) {
    this.roleForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      description: ['']
    });
  }

  ngOnInit(): void {
    this.loadPermissions();
    this.targetEntityName.set(
      this.authService.getCurrentMembership()?.entity?.name || ''
    );

    // Check if we're in edit mode
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.roleId = parseInt(id, 10);
      this.isEditMode.set(true);
      this.loadRole(this.roleId);
    }
  }

  loadPermissions(): void {
    this.permissionsService.getPermissions().subscribe({
      next: (permissions) => {
        // Filter out manage_all permissions - these are exclusive to superadmin
        const filteredPermissions = permissions.filter(p => p.action !== 'manage_all');
        this.availablePermissions.set(filteredPermissions);
      },
      error: (error) => {
        console.error('Error loading permissions:', error);
        this.snackBar.open('Error al cargar permisos', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  loadRole(id: number): void {
    this.loading.set(true);
    this.rolesService.getRole(id).subscribe({
      next: (role) => {
        this.roleForm.patchValue({
          name: role.name,
          description: role.description
        });

        // Check if this is the superadmin role
        this.isSuperadmin.set(role.name === 'superadmin');

        if (this.isSuperadmin()) {
          // Superadmin: load ALL permissions (including manage_all) and show them all as selected
          this.permissionsService.getPermissions().subscribe({
            next: (allPermissions) => {
              this.selectedPermissions.set(allPermissions);
              this.availablePermissions.set([]);
              this.loading.set(false);
            },
            error: (error) => {
              console.error('Error loading all permissions for superadmin:', error);
              this.loading.set(false);
            }
          });
        } else {
          // Regular role: filter out manage_all permissions
          if (role.permissions && role.permissions.length > 0) {
            // Filter out manage_all permissions from role's permissions
            const rolePermissions = role.permissions.filter(p => p.action !== 'manage_all');
            const rolePermissionIds = rolePermissions.map(p => p.id);
            const available = this.availablePermissions().filter(p => !rolePermissionIds.includes(p.id));
            const selected = this.availablePermissions().filter(p => rolePermissionIds.includes(p.id));

            this.availablePermissions.set(available);
            this.selectedPermissions.set(selected);
          }
          this.loading.set(false);
        }
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

  /**
   * What to show for a permission in the two lists.
   *
   * These read as "fees - manage" and "users - read_sensitive": the identifiers
   * the code uses, in English, in a Spanish application. Whoever is deciding
   * what a role can do has 79 of them to choose from, so the description
   * leads and the identifier sits underneath it. Falls back to the pair when a
   * permission has no description.
   */
  getPermissionLabel(permission: PermissionResponse): string {
    return permission.description?.trim()
      || `${permission.resource} - ${permission.action}`;
  }

  /** The technical identifier, shown on hover. */
  getPermissionCode(permission: PermissionResponse): string {
    return `${permission.resource}:${permission.action}`;
  }

  moveToSelected(permission: PermissionResponse): void {
    this.availablePermissions.update(perms =>
      perms.filter(p => p.id !== permission.id)
    );
    this.selectedPermissions.update(perms => [...perms, permission]);
  }

  moveToAvailable(permission: PermissionResponse): void {
    this.selectedPermissions.update(perms =>
      perms.filter(p => p.id !== permission.id)
    );
    this.availablePermissions.update(perms => [...perms, permission]);
  }

  moveAllToSelected(): void {
    const current = this.availablePermissions();
    this.selectedPermissions.update(perms => [...perms, ...current]);
    this.availablePermissions.set([]);
  }

  moveAllToAvailable(): void {
    const current = this.selectedPermissions();
    this.availablePermissions.update(perms => [...perms, ...current]);
    this.selectedPermissions.set([]);
  }

  onSubmit(): void {
    if (this.roleForm.invalid) {
      return;
    }

    // Prevent modification of superadmin role
    if (this.isSuperadmin()) {
      this.snackBar.open('No se puede modificar el rol superadmin', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      return;
    }

    this.loading.set(true);
    const formValue = this.roleForm.value;

    // Get selected permission IDs
    const permissionIds = this.selectedPermissions().map(p => p.id);

    if (this.isEditMode() && this.roleId) {
      // Update mode
      const roleData: RoleUpdate = {
        name: formValue.name,
        description: formValue.description,
        permission_ids: permissionIds
      };

      this.rolesService.updateRole(this.roleId, roleData).subscribe({
        next: () => {
          this.snackBar.open('Rol actualizado correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/roles']);
        },
        error: (error) => {
          console.error('Error updating role:', error);
          // The server explains name clashes — which association holds the
          // name and what to call this one instead. Swallowing that left the
          // person staring at a list where nothing by that name appears.
          const detail = error?.error?.detail;
          this.snackBar.open(detail || 'Error al actualizar el rol', 'Cerrar', {
            duration: detail ? 10000 : 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    } else {
      // Create mode
      const roleData: RoleCreate = {
        name: formValue.name,
        description: formValue.description,
        permission_ids: permissionIds.length > 0 ? permissionIds : undefined
      };

      this.rolesService.createRole(roleData).subscribe({
        next: () => {
          this.snackBar.open('Rol creado correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/roles']);
        },
        error: (error) => {
          console.error('Error creating role:', error);
          // The server explains name clashes — which association holds the
          // name and what to call this one instead. Swallowing that left the
          // person staring at a list where nothing by that name appears.
          const detail = error?.error?.detail;
          this.snackBar.open(detail || 'Error al crear el rol', 'Cerrar', {
            duration: detail ? 10000 : 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    }
  }

  onCancel(): void {
    this.router.navigate(['/roles']);
  }
}
