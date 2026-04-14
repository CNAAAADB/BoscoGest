import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatMenuModule } from '@angular/material/menu';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Capacitor } from '@capacitor/core';
import { forkJoin } from 'rxjs';
import { MagazinesService } from '../magazines.service';
import { MagazineDetails } from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-magazine-viewer',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatMenuModule
  ],
  templateUrl: './magazine-viewer.component.html',
  styleUrl: './magazine-viewer.component.css'
})
export class MagazineViewerComponent implements OnInit, OnDestroy {
  magazine = signal<MagazineDetails | null>(null);
  loading = signal<boolean>(true);
  magazineId: number | null = null;
  pdfUrl = signal<SafeResourceUrl | null>(null);
  isNative = Capacitor.isNativePlatform();
  private objectUrl: string | null = null;

  constructor(
    private magazinesService: MagazinesService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private sanitizer: DomSanitizer,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.magazineId = parseInt(id, 10);
      this.loadMagazine(this.magazineId);
    } else {
      this.snackBar.open('ID de revista no válido', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      this.router.navigate(['/magazines']);
    }
  }

  loadMagazine(id: number): void {
    this.loading.set(true);

    if (this.isNative) {
      // On native platforms, iframe PDF viewing doesn't work in WebView.
      // Just load the magazine details and offer download.
      this.magazinesService.getMagazineDetails(id).subscribe({
        next: (magazine) => {
          this.magazine.set(magazine);
          this.loading.set(false);
        },
        error: (error) => {
          console.error('Error loading magazine:', error);
          this.snackBar.open('Error al cargar la revista', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
          this.router.navigate(['/magazines']);
        }
      });
      return;
    }

    // Fetch both magazine details and PDF blob in parallel
    forkJoin({
      magazine: this.magazinesService.getMagazineDetails(id),
      pdfBlob: this.magazinesService.getMagazineFileBlob(id)
    }).subscribe({
      next: ({ magazine, pdfBlob }) => {
        this.magazine.set(magazine);

        // Create object URL from blob
        this.objectUrl = URL.createObjectURL(pdfBlob);

        // Sanitize the URL for safe use in iframe
        this.pdfUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(this.objectUrl));

        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading magazine:', error);
        this.snackBar.open('Error al cargar la revista', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/magazines']);
      }
    });
  }

  downloadMagazine(): void {
    const mag = this.magazine();
    if (mag && this.magazineId) {
      this.magazinesService.downloadMagazine(this.magazineId, mag.title);
    }
  }

  goBack(): void {
    this.router.navigate(['/magazines']);
  }

  canEditMagazine(): boolean {
    return this.authService.hasPermission('magazines', 'update');
  }

  canDeleteMagazine(): boolean {
    return this.authService.hasPermission('magazines', 'delete');
  }

  editMagazine(): void {
    if (this.magazineId) {
      this.router.navigate(['/magazines', this.magazineId, 'edit']);
    }
  }

  deleteMagazine(): void {
    const mag = this.magazine();
    if (!mag || !this.magazineId) return;

    if (confirm(`¿Estás seguro de que deseas eliminar la revista "${mag.title}"?`)) {
      this.magazinesService.deleteMagazine(this.magazineId).subscribe({
        next: () => {
          this.snackBar.open('Revista eliminada correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/magazines']);
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

  ngOnDestroy(): void {
    // Clean up object URL to prevent memory leaks
    if (this.objectUrl) {
      URL.revokeObjectURL(this.objectUrl);
    }
  }
}
