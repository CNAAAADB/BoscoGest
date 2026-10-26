import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule } from '@angular/material/dialog';
import { Capacitor } from '@capacitor/core';
import { forkJoin } from 'rxjs';
import { MagazinesService } from '../magazines.service';
import { MagazineDetails } from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist';

GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

@Component({
  selector: 'app-magazines-list',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatDialogModule
  ],
  templateUrl: './magazines-list.component.html',
  styleUrl: './magazines-list.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MagazinesListComponent implements OnInit {
  magazines = signal<MagazineDetails[]>([]);
  loading = signal<boolean>(true);
  coverImages = signal<Map<number, string>>(new Map());

  constructor(
    private magazinesService: MagazinesService,
    private router: Router,
    private snackBar: MatSnackBar,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadMagazines();
  }

  loadMagazines(): void {
    this.loading.set(true);
    this.magazinesService.getMagazines().subscribe({
      next: (magazines) => {
        this.magazines.set(magazines);

        // Skip PDF cover rendering on native platforms (pdfjs worker
        // doesn't work reliably in Android/iOS WebView). The template
        // already shows a placeholder icon when no cover image exists.
        if (magazines.length > 0 && !Capacitor.isNativePlatform()) {
          const blobRequests: { [key: number]: any } = {};
          magazines.forEach(mag => {
            blobRequests[mag.id] = this.magazinesService.getMagazineFileBlob(mag.id);
          });

          forkJoin(blobRequests).subscribe({
            next: (blobs) => {
              const imageMap = new Map<number, string>();

              const renderPromises = Object.keys(blobs).map(async (idStr) => {
                const id = parseInt(idStr, 10);
                const blob = blobs[id] as Blob;
                try {
                  const dataUrl = await this.renderFirstPage(blob);
                  imageMap.set(id, dataUrl);
                } catch (err) {
                  console.error(`Error rendering cover for magazine ${id}:`, err);
                }
              });

              Promise.all(renderPromises).then(() => {
                this.coverImages.set(imageMap);
                this.loading.set(false);
              });
            },
            error: (error) => {
              console.error('Error loading PDF previews:', error);
              this.loading.set(false);
            }
          });
        } else {
          this.loading.set(false);
        }
      },
      error: (error) => {
        console.error('Error loading magazines:', error);
        this.snackBar.open('Error al cargar las revistas', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  private async renderFirstPage(blob: Blob): Promise<string> {
    const arrayBuffer = await blob.arrayBuffer();
    const pdf = await getDocument({ data: arrayBuffer }).promise;
    const page = await pdf.getPage(1);

    const scale = 1.5;
    const viewport = page.getViewport({ scale });

    const canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    await page.render({ canvas, viewport }).promise;

    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);

    pdf.destroy();

    return dataUrl;
  }

  getCoverImage(magazineId: number): string | null {
    return this.coverImages().get(magazineId) || null;
  }

  viewMagazine(id: number): void {
    this.router.navigate(['/magazines', id]);
  }

  uploadMagazine(): void {
    this.router.navigate(['/magazines/upload']);
  }

  canCreateMagazine(): boolean {
    return this.authService.hasPermission('magazines', 'create');
  }

  canEditMagazine(): boolean {
    return this.authService.hasPermission('magazines', 'update');
  }

  canDeleteMagazine(): boolean {
    return this.authService.hasPermission('magazines', 'delete');
  }

  editMagazine(event: Event, magazineId: number): void {
    event.stopPropagation();
    this.router.navigate(['/magazines', magazineId, 'edit']);
  }

  deleteMagazine(event: Event, magazine: MagazineDetails): void {
    event.stopPropagation();

    if (confirm(`¿Estás seguro de que deseas eliminar la revista "${magazine.title}"?`)) {
      this.magazinesService.deleteMagazine(magazine.id).subscribe({
        next: () => {
          this.snackBar.open('Revista eliminada correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.loadMagazines();
        },
        error: (error) => {
          console.error('Error deleting magazine:', error);
          this.snackBar.open('Error al eliminar la revista', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
        }
      });
    }
  }
}
