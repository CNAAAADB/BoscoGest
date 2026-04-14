import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { ActivitiesService } from '../activities.service';
import { ActivityResponse } from '../../models/user.model';
import { AuthService } from '../../auth/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-activities-list',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule
  ],
  templateUrl: './activities-list.component.html',
  styleUrl: './activities-list.component.css'
})
export class ActivitiesListComponent implements OnInit {
  activities = signal<ActivityResponse[]>([]);
  loading = signal<boolean>(true);
  apiUrl = environment.apiUrl;
  showPastActivities = signal<boolean>(false);
  userRegistrations = signal<Map<number, boolean>>(new Map());

  // Check if user can create activities
  canCreateActivities = computed(() => {
    return this.authService.hasPermission('activities', 'create');
  });

  // Filtered activities based on showPastActivities toggle
  filteredActivities = computed(() => {
    const allActivities = this.activities();
    if (this.showPastActivities()) {
      return allActivities;
    }
    // Only show upcoming activities
    return allActivities.filter(activity => this.isUpcoming(activity.date));
  });

  constructor(
    private activitiesService: ActivitiesService,
    private router: Router,
    private snackBar: MatSnackBar,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadActivities();
  }

  loadActivities(): void {
    this.loading.set(true);
    this.activitiesService.getActivities().subscribe({
      next: (activities) => {
        // Sort activities by date ascending (earliest first)
        const sortedActivities = activities.sort((a, b) => {
          return new Date(a.date).getTime() - new Date(b.date).getTime();
        });
        this.activities.set(sortedActivities);
        // Check registration status for each activity
        this.checkUserRegistrations(sortedActivities);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading activities:', error);
        this.snackBar.open('Error al cargar las actividades', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  checkUserRegistrations(activities: ActivityResponse[]): void {
    const registrationsMap = new Map<number, boolean>();

    // Check registration status for each activity
    activities.forEach(activity => {
      this.activitiesService.getMyRegistration(activity.id).subscribe({
        next: (registration) => {
          registrationsMap.set(activity.id, registration !== null);
          this.userRegistrations.set(new Map(registrationsMap));
        },
        error: (error) => {
          console.error(`Error checking registration for activity ${activity.id}:`, error);
          registrationsMap.set(activity.id, false);
          this.userRegistrations.set(new Map(registrationsMap));
        }
      });
    });
  }

  isUserRegistered(activityId: number): boolean {
    return this.userRegistrations().get(activityId) || false;
  }

  createActivity(): void {
    this.router.navigate(['/activities/new']);
  }

  viewActivity(activity: ActivityResponse): void {
    this.router.navigate(['/activities', activity.id]);
  }

  registerToActivity(activity: ActivityResponse, event: Event): void {
    // Stop event propagation to prevent card click navigation
    event.stopPropagation();

    this.activitiesService.registerToActivity(activity.id).subscribe({
      next: () => {
        this.snackBar.open('Inscripción realizada correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        // Update registration status
        const currentMap = new Map(this.userRegistrations());
        currentMap.set(activity.id, true);
        this.userRegistrations.set(currentMap);
      },
      error: (error) => {
        console.error('Error registering to activity:', error);
        const errorMessage = error?.error?.detail || 'Error al inscribirse en la actividad';
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 5000,
          panelClass: 'error-snackbar'
        });
      }
    });
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

  getImageUrl(imageUrl: string | null): string {
    if (!imageUrl) {
      return 'assets/default-activity.png';
    }
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }

  isUpcoming(dateString: string): boolean {
    return new Date(dateString) > new Date();
  }

  isPast(dateString: string): boolean {
    return new Date(dateString) < new Date();
  }

  togglePastActivities(): void {
    this.showPastActivities.update(value => !value);
  }
}
