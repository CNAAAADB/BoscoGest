import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { CommunicationsService } from '../communications.service';
import { CommunicationResponse } from '../../models/user.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-communications-blog',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatPaginatorModule
  ],
  templateUrl: './communications-blog.component.html',
  styleUrl: './communications-blog.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NewsBlogComponent implements OnInit {
  newsList = signal<CommunicationResponse[]>([]);
  loading = signal<boolean>(true);
  totalNews = signal<number>(0);
  pageSize = 6;
  pageIndex = 0;
  apiUrl = environment.apiUrl;

  constructor(
    private newsService: CommunicationsService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadNewsCount();
    this.loadNews();
  }

  loadNewsCount(): void {
    this.newsService.getNewsCount('published').subscribe({
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
    this.newsService.getNewsList(skip, this.pageSize, 'published').subscribe({
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

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadNews();
    // Scroll to top on page change
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  viewNews(news: CommunicationResponse): void {
    this.router.navigate(['/communications', news.id]);
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  getExcerpt(content: string, maxLength: number = 200): string {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  }

  getImageUrl(imageUrl: string | null): string {
    if (!imageUrl) return '';
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }
}
