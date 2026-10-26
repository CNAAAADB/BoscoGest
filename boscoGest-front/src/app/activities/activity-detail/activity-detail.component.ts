import { Component, OnInit, signal, computed, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { MatDialog } from '@angular/material/dialog';
import { ActivitiesService } from '../activities.service';
import { UsersService } from '../../users/users.service';
import { ActivityResponse, ActivityRegistrationOut, UserResponse } from '../../models/user.model';
import { formatActivityDates } from '../activity-dates';
import { AuthService } from '../../auth/auth.service';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { environment } from '../../../environments/environment';

interface RegistrationWithUser extends ActivityRegistrationOut {
  user?: UserResponse;
}

@Component({
  selector: 'app-activity-detail',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatChipsModule,
    MatTableModule
  ],
  templateUrl: './activity-detail.component.html',
  styleUrl: './activity-detail.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ActivityDetailComponent implements OnInit {
  activity = signal<ActivityResponse | null>(null);
  loading = signal<boolean>(true);
  activityId: number | null = null;
  apiUrl = environment.apiUrl;

  // Registrations
  registrations = signal<RegistrationWithUser[]>([]);
  loadingRegistrations = signal<boolean>(false);

  // Permissions
  canRegister = signal<boolean>(false);
  isRegistered = signal<boolean>(false);
  currentUserId = computed(() => this.authService.getCurrentUser()?.id);

  // Check if user can manage activities
  canManageActivities = computed(() => {
    return this.authService.hasPermission('activities', 'manage');
  });

  // Check if user can edit activities
  canEditActivities = computed(() => {
    return this.authService.hasPermission('activities', 'update');
  });

  // Check if user can delete activities
  canDeleteActivities = computed(() => {
    return this.authService.hasPermission('activities', 'delete');
  });

  // Show admin actions (if user has any management permission for activities)
  showAdminActions = computed(() => {
    return this.canManageActivities() || this.canEditActivities() || this.canDeleteActivities();
  });

  // Only the activity creator or an activities manager can create the chat group
  canCreateChatGroup = computed(() => {
    const activity = this.activity();
    if (!activity) return false;
    return activity.created_by_id === this.currentUserId() || this.canManageActivities();
  });

  creatingChatGroup = signal<boolean>(false);

  // Computed lists
  acceptedRegistrations = computed(() =>
    this.registrations().filter(r => r.status === 'accepted')
  );

  waitlistRegistrations = computed(() =>
    this.registrations().filter(r => r.status === 'waitlist')
  );

  pendingRegistrations = computed(() =>
    this.registrations().filter(r => r.status === 'pending')
  );

  pendingAndWaitlistRegistrations = computed(() =>
    this.registrations().filter(r => r.status === 'pending' || r.status === 'waitlist')
  );

  displayedColumns: string[] = ['user', 'status', 'registered_at', 'actions'];

  constructor(
    private activitiesService: ActivitiesService,
    private usersService: UsersService,
    private route: ActivatedRoute,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.activityId = parseInt(id, 10);
      this.loadActivity(this.activityId);
      // Load registrations if user has manage permission
      if (this.canManageActivities()) {
        this.loadRegistrations();
      }
    } else {
      this.router.navigate(['/activities']);
    }
  }

  loadActivity(id: number): void {
    this.loading.set(true);
    this.activitiesService.getActivity(id).subscribe({
      next: (activity) => {
        this.activity.set(activity);
        this.checkIfUserIsRegistered();
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading activity:', error);
        this.snackBar.open('Error al cargar la actividad', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/activities']);
      }
    });
  }

  loadRegistrations(): void {
    if (!this.activityId) return;

    this.loadingRegistrations.set(true);
    this.activitiesService.getRegistrations(this.activityId).subscribe({
      next: async (registrations) => {
        // Load user details for each registration
        const registrationsWithUsers = await Promise.all(
          registrations.map(async (reg) => {
            try {
              const user = await this.usersService.getUser(reg.user_id).toPromise();
              return { ...reg, user };
            } catch (error) {
              console.error('Error loading user:', error);
              return reg;
            }
          })
        );
        this.registrations.set(registrationsWithUsers);
        this.loadingRegistrations.set(false);
      },
      error: (error) => {
        console.error('Error loading registrations:', error);
        this.loadingRegistrations.set(false);
      }
    });
  }

  checkIfUserIsRegistered(): void {
    if (!this.activityId) return;

    // Use the new endpoint to check registration status
    this.activitiesService.getMyRegistration(this.activityId).subscribe({
      next: (registration) => {
        this.isRegistered.set(registration !== null);
      },
      error: (error) => {
        console.error('Error checking registration status:', error);
        this.isRegistered.set(false);
      }
    });
  }

  registerToActivity(): void {
    if (!this.activityId) return;

    this.activitiesService.registerToActivity(this.activityId).subscribe({
      next: () => {
        this.snackBar.open('Inscripción realizada correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        // Reload registration status
        this.checkIfUserIsRegistered();
        // Reload registrations list if user can manage activities
        if (this.canManageActivities()) {
          this.loadRegistrations();
        }
      },
      error: (error) => {
        console.error('Error registering to activity:', error);
        const errorMessage = error?.error?.detail || 'Error al inscribirse en la actividad';
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  acceptRegistration(registration: RegistrationWithUser): void {
    if (!this.activityId) return;

    this.activitiesService.acceptRegistration(this.activityId, registration.user_id).subscribe({
      next: () => {
        this.snackBar.open('Inscripción aceptada', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.loadRegistrations();
      },
      error: (error) => {
        console.error('Error accepting registration:', error);
        const errorMessage = error?.error?.detail || 'Error al aceptar la inscripción';
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  rejectRegistration(registration: RegistrationWithUser): void {
    if (!this.activityId) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Rechazar inscripción',
        message: `¿Está seguro de que desea rechazar la inscripción de ${registration.user?.name} ${registration.user?.surname}?`,
        confirmText: 'Rechazar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result && this.activityId) {
        this.activitiesService.rejectRegistration(this.activityId, registration.user_id).subscribe({
          next: () => {
            this.snackBar.open('Inscripción rechazada', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.loadRegistrations();
          },
          error: (error) => {
            console.error('Error rejecting registration:', error);
            this.snackBar.open('Error al rechazar la inscripción', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }

  createChatGroup(): void {
    if (!this.activityId || this.creatingChatGroup()) return;

    this.creatingChatGroup.set(true);
    this.activitiesService.createChatGroup(this.activityId).subscribe({
      next: (result) => {
        this.creatingChatGroup.set(false);
        this.snackBar.open('Grupo de chat creado correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.router.navigate(['/chat'], { queryParams: { conversation: result.conversation_id } });
      },
      error: (error) => {
        this.creatingChatGroup.set(false);
        const errorMessage = error?.error?.detail || 'Error al crear el grupo de chat';
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  editActivity(): void {
    if (this.activityId) {
      this.router.navigate(['/activities', this.activityId, 'edit']);
    }
  }

  deleteActivity(): void {
    if (!this.activityId) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Eliminar actividad',
        message: '¿Está seguro de que desea eliminar esta actividad? Esta acción no se puede deshacer.',
        confirmText: 'Eliminar',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result && this.activityId) {
        this.activitiesService.deleteActivity(this.activityId).subscribe({
          next: () => {
            this.snackBar.open('Actividad eliminada correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.router.navigate(['/activities']);
          },
          error: (error) => {
            console.error('Error deleting activity:', error);
            this.snackBar.open('Error al eliminar la actividad', 'Cerrar', {
              duration: 3000,
              panelClass: 'error-snackbar'
            });
          }
        });
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/activities']);
  }

  formatDates(activity: ActivityResponse): string {
    return formatActivityDates(activity);
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

  getStatusLabel(status: string): string {
    const statusMap: { [key: string]: string } = {
      'accepted': 'Aceptado',
      'pending': 'Pendiente',
      'rejected': 'Rechazado',
      'waitlist': 'Lista de espera'
    };
    return statusMap[status] || status;
  }

  getStatusClass(status: string): string {
    return `status-${status}`;
  }
}
