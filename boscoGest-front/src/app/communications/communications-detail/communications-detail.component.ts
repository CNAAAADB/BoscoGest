import { Component, OnInit, signal, computed, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatDividerModule } from '@angular/material/divider';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { CommunicationsService } from '../communications.service';
import {
  CommunicationWithCommentsResponse,
  CommentResponse,
  CommunicationStatus,
  COMMUNICATION_STATUS_LABELS,
  COMMUNICATION_STATUS_COLORS
} from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-communications-detail',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatFormFieldModule,
    MatInputModule,
    MatDividerModule,
    MatSnackBarModule
  ],
  templateUrl: './communications-detail.component.html',
  styleUrl: './communications-detail.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NewsDetailComponent implements OnInit {
  news = signal<CommunicationWithCommentsResponse | null>(null);
  loading = signal<boolean>(true);
  commentForm: FormGroup;
  submittingComment = signal<boolean>(false);
  apiUrl = environment.apiUrl;

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

  canCreateComment = computed(() => {
    return this.authService.hasPermission('comment', 'create');
  });

  canEditComment = computed(() => {
    return this.authService.hasPermission('comment', 'edit');
  });

  canDeleteComment = computed(() => {
    return this.authService.hasPermission('comment', 'delete');
  });

  currentUserId = computed(() => {
    return this.authService.getCurrentUser()?.id;
  });

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private newsService: CommunicationsService,
    private authService: AuthService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    this.commentForm = this.fb.group({
      content: ['', [Validators.required, Validators.minLength(1)]]
    });
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadNews(parseInt(id, 10));
    }
  }

  loadNews(id: number): void {
    this.loading.set(true);
    this.newsService.getNews(id).subscribe({
      next: (news) => {
        this.news.set(news);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading news:', error);
        this.snackBar.open('Error al cargar la comunicación', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/communications']);
      }
    });
  }

  editNews(): void {
    const news = this.news();
    if (news) {
      this.router.navigate(['/communications', news.id, 'edit']);
    }
  }

  deleteNews(): void {
    const news = this.news();
    if (!news) return;

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
            this.router.navigate(['/communications']);
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

  submitComment(): void {
    if (this.commentForm.invalid) return;

    const news = this.news();
    if (!news) return;

    this.submittingComment.set(true);
    const commentData = this.commentForm.value;

    this.newsService.createComment(news.id, commentData).subscribe({
      next: () => {
        this.snackBar.open('Comentario publicado', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.commentForm.reset();
        this.loadNews(news.id);
        this.submittingComment.set(false);
      },
      error: (error) => {
        console.error('Error creating comment:', error);
        this.snackBar.open('Error al publicar el comentario', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.submittingComment.set(false);
      }
    });
  }

  deleteComment(comment: CommentResponse): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Confirmar eliminación',
        message: '¿Está seguro de que desea eliminar este comentario?',
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.newsService.deleteComment(comment.id).subscribe({
          next: () => {
            this.snackBar.open('Comentario eliminado', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            const news = this.news();
            if (news) {
              this.loadNews(news.id);
            }
          },
          error: (error) => {
            console.error('Error deleting comment:', error);
            this.snackBar.open('Error al eliminar el comentario', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }

  getStatusLabel(status: string): string {
    return COMMUNICATION_STATUS_LABELS[status as CommunicationStatus] ?? status;
  }

  getStatusColor(status: string): string {
    return COMMUNICATION_STATUS_COLORS[status as CommunicationStatus] ?? '#9e9e9e';
  }

  transitionStatus(targetStatus: CommunicationStatus): void {
    const news = this.news();
    if (!news) return;

    this.newsService.transitionStatus(news.id, targetStatus).subscribe({
      next: () => {
        const label = this.getStatusLabel(targetStatus);
        this.snackBar.open(`Comunicación movida a "${label}"`, 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.loadNews(news.id);
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

  backToList(): void {
    this.router.navigate(['/communications']);
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  formatShortDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  getImageUrl(imageUrl: string | null): string {
    if (!imageUrl) return '';
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }
}
