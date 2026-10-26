import { Component, OnInit, OnDestroy, signal, computed, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ResourcesService } from '../resources.service';
import { ResourceDetails } from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';
import { ConfirmDialogComponent, ConfirmDialogData } from '../../confirm-dialog/confirm-dialog.component';
@Component({
  selector: 'app-resource-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatDialogModule,
  ],
  templateUrl: './resource-detail.component.html',
  styleUrl: './resource-detail.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResourceDetailComponent implements OnInit, OnDestroy {
  resource = signal<ResourceDetails | null>(null);
  loading = signal<boolean>(true);
  fileUrl = signal<SafeResourceUrl | null>(null);
  private objectUrl: string | null = null;

  canEdit = computed(() => this.authService.hasPermission('resources', 'update'));
  canDelete = computed(() => this.authService.hasPermission('resources', 'delete'));

  constructor(
    private resourcesService: ResourcesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar,
    private authService: AuthService,
    private dialog: MatDialog,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadResource(parseInt(id, 10));
    }
  }

  loadResource(id: number): void {
    this.loading.set(true);
    this.resourcesService.getResource(id).subscribe({
      next: (resource) => {
        this.resource.set(resource);
        this.loading.set(false);

        // Load file preview for documents (PDF) and images
        if (resource.file_path) {
          this.loadFilePreview(resource);
        }
      },
      error: () => {
        this.snackBar.open('Error al cargar el recurso', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
        this.router.navigate(['/resources']);
      }
    });
  }

  private loadFilePreview(resource: ResourceDetails): void {
    if (resource.resource_type === 'image' || resource.resource_type === 'document') {
      this.resourcesService.getResourceFileBlob(resource.id).subscribe({
        next: (blob) => {
          this.objectUrl = URL.createObjectURL(blob);
          const safeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.objectUrl);
          this.fileUrl.set(safeUrl);
        },
        error: () => {} // Non-critical, don't show error
      });
    }
  }

  getTypeIcon(type: string): string {
    switch (type) {
      case 'link': return 'link';
      case 'document': return 'description';
      case 'image': return 'image';
      case 'video': return 'videocam';
      default: return 'insert_drive_file';
    }
  }

  getTypeLabel(type: string): string {
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

  openUrl(): void {
    const r = this.resource();
    if (r?.url) {
      window.open(r.url, '_blank');
    }
  }

  downloadFile(): void {
    const r = this.resource();
    if (r) {
      const filename = r.original_filename || `${r.title}`;
      this.resourcesService.downloadResource(r.id, filename);
    }
  }

  editResource(): void {
    const r = this.resource();
    if (r) {
      this.router.navigate(['/resources', r.id, 'edit']);
    }
  }

  deleteResource(): void {
    const r = this.resource();
    if (!r) return;

    this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Eliminar Recurso',
        message: `¿Estás seguro de que deseas eliminar "${r.title}"?`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar',
      } as ConfirmDialogData
    }).afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.resourcesService.deleteResource(r.id).subscribe({
          next: () => {
            this.snackBar.open('Recurso eliminado correctamente', 'Cerrar', { duration: 3000 });
            this.router.navigate(['/resources']);
          },
          error: () => {
            this.snackBar.open('Error al eliminar el recurso', 'Cerrar', { duration: 3000 });
          }
        });
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/resources']);
  }

  ngOnDestroy(): void {
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
    }
  }
}
