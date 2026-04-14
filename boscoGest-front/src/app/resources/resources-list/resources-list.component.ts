import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ResourcesService } from '../resources.service';
import { ResourceDetails, ResourceType, ResourceCategoryResponse } from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';
import { ConfirmDialogComponent, ConfirmDialogData } from '../../confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-resources-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './resources-list.component.html',
  styleUrl: './resources-list.component.css'
})
export class ResourcesListComponent implements OnInit {
  resources = signal<ResourceDetails[]>([]);
  categories = signal<ResourceCategoryResponse[]>([]);
  loading = signal<boolean>(true);

  // Filters
  searchQuery = signal<string>('');
  selectedType = signal<ResourceType | ''>('');
  selectedCategoryId = signal<number | null>(null);

  filteredResources = computed(() => {
    let resources = this.resources();
    const search = this.searchQuery().toLowerCase();
    const type = this.selectedType();
    const categoryId = this.selectedCategoryId();

    if (search) {
      resources = resources.filter(r =>
        r.title.toLowerCase().includes(search) ||
        (r.description || '').toLowerCase().includes(search) ||
        (r.tags || '').toLowerCase().includes(search)
      );
    }
    if (type) {
      resources = resources.filter(r => r.resource_type === type);
    }
    if (categoryId) {
      resources = resources.filter(r => r.category_id === categoryId);
    }
    return resources;
  });

  canCreate = computed(() => this.authService.hasPermission('resources', 'create'));
  canEdit = computed(() => this.authService.hasPermission('resources', 'update'));
  canDelete = computed(() => this.authService.hasPermission('resources', 'delete'));

  constructor(
    private resourcesService: ResourcesService,
    private router: Router,
    private snackBar: MatSnackBar,
    private authService: AuthService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.loadResources();
    this.loadCategories();
  }

  loadResources(): void {
    this.loading.set(true);
    this.resourcesService.getResources().subscribe({
      next: (resources) => {
        this.resources.set(resources);
        this.loading.set(false);
      },
      error: () => {
        this.snackBar.open('Error al cargar los recursos', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  loadCategories(): void {
    const membership = this.authService.getCurrentMembership();
    if (membership) {
      this.resourcesService.getCategories(membership.entity_id).subscribe({
        next: (categories) => this.categories.set(categories),
        error: () => {} // Categories are optional
      });
    }
  }

  getTypeIcon(type: ResourceType): string {
    switch (type) {
      case 'link': return 'link';
      case 'document': return 'description';
      case 'image': return 'image';
      case 'video': return 'videocam';
      default: return 'insert_drive_file';
    }
  }

  getTypeLabel(type: ResourceType): string {
    switch (type) {
      case 'link': return 'Enlace';
      case 'document': return 'Documento';
      case 'image': return 'Imagen';
      case 'video': return 'Video';
      default: return type;
    }
  }

  getTagsList(tags: string | null): string[] {
    if (!tags) return [];
    return tags.split(',').map(t => t.trim()).filter(t => t);
  }

  viewResource(id: number): void {
    this.router.navigate(['/resources', id]);
  }

  createResource(): void {
    this.router.navigate(['/resources/new']);
  }

  editResource(event: Event, id: number): void {
    event.stopPropagation();
    this.router.navigate(['/resources', id, 'edit']);
  }

  deleteResource(event: Event, resource: ResourceDetails): void {
    event.stopPropagation();
    this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Eliminar Recurso',
        message: `¿Estás seguro de que deseas eliminar "${resource.title}"?`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar',
      } as ConfirmDialogData
    }).afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.resourcesService.deleteResource(resource.id).subscribe({
          next: () => {
            this.snackBar.open('Recurso eliminado correctamente', 'Cerrar', { duration: 3000 });
            this.loadResources();
          },
          error: () => {
            this.snackBar.open('Error al eliminar el recurso', 'Cerrar', { duration: 3000 });
          }
        });
      }
    });
  }

  clearFilters(): void {
    this.searchQuery.set('');
    this.selectedType.set('');
    this.selectedCategoryId.set(null);
  }

  onSearchChange(value: string): void {
    this.searchQuery.set(value);
  }

  onTypeChange(value: ResourceType | ''): void {
    this.selectedType.set(value);
  }

  onCategoryChange(value: number | null): void {
    this.selectedCategoryId.set(value);
  }
}
