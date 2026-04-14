import { Component, OnInit, signal, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FullCalendarComponent, FullCalendarModule } from '@fullcalendar/angular';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import esLocale from '@fullcalendar/core/locales/es';
import { ActivitiesService } from '../activities/activities.service';
import { CommunicationsService } from '../communications/communications.service';
import { ActivityResponse, CommunicationResponse } from '../models/user.model';
import { Router } from '@angular/router';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-dashboard',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatButtonToggleModule,
    MatSnackBarModule,
    FullCalendarModule
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  @ViewChild('calendar') calendarComponent!: FullCalendarComponent;

  loading = signal<boolean>(true);
  activities = signal<ActivityResponse[]>([]);
  upcomingActivities = signal<ActivityResponse[]>([]);
  calendarView = signal<'dayGridMonth' | 'timeGridWeek'>('dayGridMonth');
  currentCarouselIndex = signal<number>(0);

  // News signals
  recentNews = signal<CommunicationResponse[]>([]);
  selectedNews = signal<CommunicationResponse | null>(null);
  newsPageIndex = signal<number>(0);
  newsPageSize = 5;
  totalNews = signal<number>(0);
  apiUrl = environment.apiUrl;

  calendarOptions: CalendarOptions = {
    plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    locale: esLocale,
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: ''
    },
    height: 'auto',
    events: [],
    eventClick: this.handleEventClick.bind(this),
    eventDisplay: 'block',
    dayMaxEvents: 3,
    nowIndicator: true,
    navLinks: true,
    editable: false,
    selectable: false
  };

  constructor(
    private activitiesService: ActivitiesService,
    private newsService: CommunicationsService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadActivities();
    this.loadNewsCount();
    this.loadNews();
  }

  loadActivities(): void {
    this.loading.set(true);
    this.activitiesService.getActivities().subscribe({
      next: (activities) => {
        this.activities.set(activities);

        // Convert activities to calendar events
        const events: EventInput[] = activities.map(activity => ({
          id: activity.id.toString(),
          title: activity.title,
          start: new Date(activity.date),
          backgroundColor: '#3D4E7C',
          borderColor: '#D4A76A',
          extendedProps: {
            activity: activity
          }
        }));

        // Update calendar events
        this.calendarOptions = {
          ...this.calendarOptions,
          events: events
        };

        // Get upcoming activities (sorted by date, future only)
        const now = new Date();
        const upcoming = activities
          .filter(activity => new Date(activity.date) >= now)
          .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

        this.upcomingActivities.set(upcoming);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading activities:', error);
        this.loading.set(false);
      }
    });
  }

  handleEventClick(clickInfo: any): void {
    const activityId = clickInfo.event.id;
    if (activityId) {
      this.router.navigate(['/activities', activityId]);
    }
  }

  toggleCalendarView(): void {
    const currentView = this.calendarView();
    const newView = currentView === 'dayGridMonth' ? 'timeGridWeek' : 'dayGridMonth';
    this.calendarView.set(newView);

    // Use FullCalendar API to change view
    const calendarApi = this.calendarComponent.getApi();
    calendarApi.changeView(newView);
  }

  getViewButtonText(): string {
    return this.calendarView() === 'dayGridMonth' ? 'Vista Semanal' : 'Vista Mensual';
  }

  // Carousel methods
  get visibleActivities(): ActivityResponse[] {
    const start = this.currentCarouselIndex();
    return this.upcomingActivities().slice(start, start + 3);
  }

  get hasMoreActivities(): boolean {
    return this.currentCarouselIndex() + 3 < this.upcomingActivities().length;
  }

  get hasPreviousActivities(): boolean {
    return this.currentCarouselIndex() > 0;
  }

  nextActivities(): void {
    if (this.hasMoreActivities) {
      this.currentCarouselIndex.update(index => index + 3);
    }
  }

  previousActivities(): void {
    if (this.hasPreviousActivities) {
      this.currentCarouselIndex.update(index => index - 3);
    }
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      weekday: 'long',
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
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  viewActivityDetails(activityId: number): void {
    this.router.navigate(['/activities', activityId]);
  }

  registerToActivity(activityId: number, event: Event): void {
    // Prevent navigation to activity details when clicking the button
    event.stopPropagation();

    this.activitiesService.registerToActivity(activityId).subscribe({
      next: (registration) => {
        this.snackBar.open('Te has inscrito correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        // Reload activities to refresh the list
        this.loadActivities();
      },
      error: (error) => {
        console.error('Error registering to activity:', error);
        const message = error.error?.detail || 'Error al inscribirse en la actividad';
        this.snackBar.open(message, 'Cerrar', {
          duration: 5000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  // News methods
  loadNewsCount(): void {
    this.newsService.getNewsCount().subscribe({
      next: (response: { total: number }) => {
        this.totalNews.set(response.total);
      },
      error: (error: any) => {
        console.error('Error loading news count:', error);
      }
    });
  }

  loadNews(): void {
    const skip = this.newsPageIndex() * this.newsPageSize;
    this.newsService.getNewsList(skip, this.newsPageSize).subscribe({
      next: (news: CommunicationResponse[]) => {
        this.recentNews.set(news);
        // Auto-select first news if none selected
        if (news.length > 0 && !this.selectedNews()) {
          this.selectedNews.set(news[0]);
        }
      },
      error: (error: any) => {
        console.error('Error loading news:', error);
      }
    });
  }

  selectNews(news: CommunicationResponse): void {
    this.selectedNews.set(news);
  }

  viewNewsDetail(): void {
    const news = this.selectedNews();
    if (news) {
      this.router.navigate(['/communications', news.id]);
    }
  }

  formatNewsDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  }

  getNewsExcerpt(content: string, maxLength: number = 200): string {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  }

  onNewsPageChange(direction: 'prev' | 'next'): void {
    const currentIndex = this.newsPageIndex();
    const maxIndex = Math.ceil(this.totalNews() / this.newsPageSize) - 1;

    if (direction === 'prev' && currentIndex > 0) {
      this.newsPageIndex.set(currentIndex - 1);
      this.loadNews();
    } else if (direction === 'next' && currentIndex < maxIndex) {
      this.newsPageIndex.set(currentIndex + 1);
      this.loadNews();
    }
  }

  get hasPreviousNews(): boolean {
    return this.newsPageIndex() > 0;
  }

  get hasMoreNews(): boolean {
    const maxIndex = Math.ceil(this.totalNews() / this.newsPageSize) - 1;
    return this.newsPageIndex() < maxIndex;
  }

  get totalNewsPages(): number {
    return Math.ceil(this.totalNews() / this.newsPageSize);
  }

  getImageUrl(imageUrl: string | null): string {
    if (!imageUrl) return '';
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }
}
