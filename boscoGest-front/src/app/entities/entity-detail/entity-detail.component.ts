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
import { EntitiesService } from '../entities.service';
import { EntityDeletionService } from '../entity-deletion.service';
import { EntityDetails, RoleResponse } from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';

interface UserMembership {
  userId: number;
  userName: string;
  roleName: string;
  isActive: boolean;
}

@Component({
  selector: 'app-entity-detail',
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
  templateUrl: './entity-detail.component.html',
  styleUrl: './entity-detail.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntityDetailComponent implements OnInit {
  entity = signal<EntityDetails | null>(null);
  loading = signal<boolean>(true);
  entityId: number | null = null;
  rolesDisplayedColumns: string[] = ['roleId', 'roleName', 'description'];
  usersDisplayedColumns: string[] = ['userId', 'userName', 'roleName', 'isActive'];

  getLevelName(level: number): string {
    const levelMap: { [key: number]: string } = {
      1: 'Superentity',
      2: 'Confederación',
      3: 'Federación',
      4: 'Asociación Local'
    };
    return levelMap[level] || `Nivel ${level}`;
  }

  // Get unique roles from memberships
  associatedRoles = computed<RoleResponse[]>(() => {
    const currentEntity = this.entity();
    if (!currentEntity?.memberships) return [];

    const uniqueRoles = new Map<number, RoleResponse>();
    currentEntity.memberships.forEach(membership => {
      if (membership.role && !uniqueRoles.has(membership.role.id)) {
        uniqueRoles.set(membership.role.id, membership.role);
      }
    });

    return Array.from(uniqueRoles.values());
  });

  // Get user memberships with their roles
  userMemberships = computed<UserMembership[]>(() => {
    const currentEntity = this.entity();
    if (!currentEntity?.memberships) return [];

    return currentEntity.memberships
      .filter(m => m.user && m.role)
      .map(m => ({
        userId: m.user!.id,
        userName: `${m.user!.name} ${m.user!.surname}`,
        roleName: m.role!.name,
        isActive: m.is_active
      }));
  });

  // Check if user can edit entities
  canEditEntities = computed(() => {
    return this.authService.hasPermission('entities', 'update');
  });

  // Check if user can delete entities
  canDeleteEntities = computed(() => {
    return this.authService.hasPermission('entities', 'delete');
  });

  // Show admin sections (if user has any management permission for entities)
  showAdminSections = computed(() => {
    return this.canEditEntities() || this.canDeleteEntities();
  });

  constructor(
    private entitiesService: EntitiesService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private authService: AuthService,
    private entityDeletion: EntityDeletionService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.entityId = parseInt(id, 10);
      this.loadEntity(this.entityId);
    } else {
      this.router.navigate(['/entities']);
    }
  }

  loadEntity(id: number): void {
    this.loading.set(true);
    this.entitiesService.getEntityDetails(id).subscribe({
      next: (entity) => {
        this.entity.set(entity);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading entity:', error);
        this.snackBar.open('Error al cargar la asociación', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/entities']);
      }
    });
  }

  editEntity(): void {
    if (this.entityId) {
      this.router.navigate(['/entities', this.entityId, 'edit']);
    }
  }

  deleteEntity(): void {
    const entityData = this.entity();
    if (!entityData || !this.entityId) return;

    // The rules and the wording live in EntityDeletionService, so this screen
    // and the list cannot drift apart.
    this.entityDeletion
      .confirmAndDelete({ id: this.entityId, name: entityData.name })
      .subscribe({
        next: (deleted) => {
          if (!deleted) {
            return;
          }
          this.snackBar.open('Asociación eliminada correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/entities']);
        },
        error: (error) => {
          console.error('Error deleting entity:', error);
          this.snackBar.open(
            error?.error?.detail || 'Error al eliminar la asociación',
            'Cerrar',
            { duration: 5000, panelClass: 'error-snackbar' }
          );
        }
      });
  }

  goBack(): void {
    this.router.navigate(['/entities']);
  }

  associateUser(): void {
    if (this.entityId) {
      this.router.navigate(['/entities', this.entityId, 'associate-user']);
    }
  }
}
