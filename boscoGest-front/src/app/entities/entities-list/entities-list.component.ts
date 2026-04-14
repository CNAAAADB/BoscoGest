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
import { MatTooltipModule } from '@angular/material/tooltip';
import { EntitiesService } from '../entities.service';
import { EntityResponse, MembershipDetails } from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { AuthService } from '../../auth/auth.service';
import { MembershipsService } from '../../users/memberships.service';

@Component({
  selector: 'app-entities-list',
  imports: [
    CommonModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule
  ],
  templateUrl: './entities-list.component.html',
  styleUrl: './entities-list.component.css'
})
export class EntitiesListComponent implements OnInit {
  entities = signal<EntityResponse[]>([]);
  loading = signal<boolean>(true);
  userMemberships = signal<MembershipDetails[]>([]);
  displayedColumns: string[] = ['id', 'name', 'role', 'type', 'parent', 'actions'];

  // Check if user can create entities
  canCreateEntities = computed(() => {
    return this.authService.hasPermission('entities', 'create');
  });

  // Check if user can edit a specific entity
  canEditEntity(entityId: number): boolean {
    return this.authService.hasEntityPermission(entityId, 'update');
  }

  // Check if user can delete a specific entity
  canDeleteEntity(entityId: number): boolean {
    return this.authService.hasEntityPermission(entityId, 'delete');
  }

  // Get current membership ID
  currentMembershipId = computed(() => {
    const membership = this.authService.getCurrentMembership();
    return membership?.id;
  });

  getLevelName(level: number): string {
    const levelMap: { [key: number]: string } = {
      1: 'Superentity',
      2: 'Confederación',
      3: 'Federación',
      4: 'Asociación Local'
    };
    return levelMap[level] || `Nivel ${level}`;
  }

  getUserRoleInEntity(entityId: number): string {
    const membership = this.getMembershipForEntity(entityId);
    return membership?.role?.name || '-';
  }

  constructor(
    private entitiesService: EntitiesService,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private authService: AuthService,
    private membershipsService: MembershipsService
  ) {}

  ngOnInit(): void {
    this.loadEntities();
    this.loadUserMemberships();
  }

  loadEntities(): void {
    this.loading.set(true);
    this.entitiesService.getEntities().subscribe({
      next: (entities) => {
        this.entities.set(entities);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading entities:', error);
        this.snackBar.open('Error al cargar las asociaciones', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  loadUserMemberships(): void {
    this.membershipsService.getMemberships().subscribe({
      next: (memberships) => {
        this.userMemberships.set(memberships);
      },
      error: (error) => {
        console.error('Error loading user memberships:', error);
      }
    });
  }

  getMembershipForEntity(entityId: number): MembershipDetails | undefined {
    return this.userMemberships().find(m => m.entity_id === entityId && m.is_active);
  }


  createEntity(): void {
    this.router.navigate(['/entities/new']);
  }

  viewEntity(entity: EntityResponse): void {
    this.router.navigate(['/entities', entity.id]);
  }

  editEntity(entity: EntityResponse): void {
    this.router.navigate(['/entities', entity.id, 'edit']);
  }

  deleteEntity(entity: EntityResponse): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Confirmar eliminación',
        message: `¿Está seguro de que desea eliminar la asociación "${entity.name}"? Esta acción eliminará todas las membresías y entidades hijas asociadas.`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.entitiesService.deleteEntity(entity.id).subscribe({
          next: () => {
            this.snackBar.open('Asociación eliminada correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.loadEntities();
          },
          error: (error) => {
            console.error('Error deleting entity:', error);
            this.snackBar.open('Error al eliminar la asociación', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }
}
