import { Component, OnInit, signal, computed, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { CommunicationsService } from '../communications.service';
import {
  CommunicationResponse,
  CommunicationStatus,
  COMMUNICATION_STATUS_LABELS,
  COMMUNICATION_STATUS_COLORS
} from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { AuthService } from '../../auth/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-communications-list',
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatPaginatorModule,
    MatTableModule,
    MatTooltipModule,
    MatSelectModule,
    MatFormFieldModule,
    MatChipsModule,
  ],
  templateUrl: './communications-list.component.html',
  styleUrl: './communications-list.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NewsListComponent implements OnInit {
  newsList = signal<CommunicationResponse[]>([]);
  loading = signal<boolean>(true);
  totalNews = signal<number>(0);
  pageSize = 10;
  pageIndex = 0;
  displayedColumns: string[] = ['image', 'title', 'status', 'date', 'actions'];
  apiUrl = environment.apiUrl;
  statusFilter = signal<CommunicationStatus | ''>('');

  getStatusLabel(status: string): string {
    return COMMUNICATION_STATUS_LABELS[status as CommunicationStatus] ?? status;
  }

  getStatusColor(status: string): string {
    return COMMUNICATION_STATUS_COLORS[status as CommunicationStatus] ?? '#9e9e9e';
  }

  canCreateNews = computed(() => {
    return this.authService.hasPermission('communications', 'create');
  });

  canEditNews = computed(() => {
    return this.authService.hasPermission('communications', 'edit');
  });

  canDeleteNews = computed(() => {
    return this.authService.hasPermission('communications', 'delete');
  });

  canPublishNews = computed(() => {
    return this.authService.hasPermission('communications', 'publish');
  });

  canReviewNews = computed(() => {
    return this.authService.hasPermission('communications', 'review');
  });

  constructor(
    private newsService: CommunicationsService,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadNewsCount();
    this.loadNews();
  }

  loadNewsCount(): void {
    const status = this.statusFilter() || undefined;
    this.newsService.getNewsCount(status).subscribe({
      next: (response) => {
        this.totalNews.set(response.total);
      },
      error: (error) => {
        console.error('Error loading news count:', error);
      }
    });
  }

  loadNews(): void {
    this.loading.set(true);
    const skip = this.pageIndex * this.pageSize;
    const status = this.statusFilter() || undefined;
    this.newsService.getNewsList(skip, this.pageSize, status).subscribe({
      next: (news) => {
        this.newsList.set(news);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading news:', error);
        this.snackBar.open('Error al cargar las comunicaciones', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  onStatusFilterChange(value: CommunicationStatus | ''): void {
    this.statusFilter.set(value);
    this.pageIndex = 0;
    this.loadNewsCount();
    this.loadNews();
  }

  transitionStatus(news: CommunicationResponse, targetStatus: CommunicationStatus): void {
    this.newsService.transitionStatus(news.id, targetStatus).subscribe({
      next: () => {
        const label = this.getStatusLabel(targetStatus);
        this.snackBar.open(`Comunicación movida a "${label}"`, 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.loadNews();
        this.loadNewsCount();
      },
      error: (error) => {
        console.error('Error transitioning status:', error);
        this.snackBar.open(
          error.error?.detail || 'Error al cambiar el estado',
          'Cerrar',
          { duration: 3000, panelClass: 'error-snackbar' }
        );
      }
    });
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadNews();
    // Scroll to top on page change
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  createNews(): void {
    this.router.navigate(['/communications/new']);
  }

  viewNews(news: CommunicationResponse): void {
    this.router.navigate(['/communications', news.id]);
  }

  editNews(news: CommunicationResponse): void {
    this.router.navigate(['/communications', news.id, 'edit']);
  }

  deleteNews(news: CommunicationResponse): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Confirmar eliminación',
        message: `¿Está seguro de que desea eliminar la comunicación "${news.title}"? Esta acción no se puede deshacer.`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.newsService.deleteNews(news.id).subscribe({
          next: () => {
            this.snackBar.open('Comunicación eliminada correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.loadNews();
          },
          error: (error) => {
            console.error('Error deleting news:', error);
            this.snackBar.open('Error al eliminar la comunicación', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  getExcerpt(content: string, maxLength: number = 150): string {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  }

  getImageUrl(imageUrl: string | null): string {
    if (!imageUrl) return '';
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }
}
