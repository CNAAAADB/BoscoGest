import { Component, OnInit, OnDestroy, signal, inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Subscription } from 'rxjs';

import { AuthService } from '../auth.service';
import { MembershipRequestService } from '../../membership-requests/membership-request.service';
import { NotificationService } from '../../notifications/notification.service';
import { MembershipRequestResponse, NotificationResponse } from '../../models/user.model';

@Component({
  selector: 'app-pending-approval',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDialogModule,
  ],
  templateUrl: './pending-approval.component.html',
  styleUrl: './pending-approval.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PendingApprovalComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private querySub: Subscription | null = null;
  private router = inject(Router);
  private authService = inject(AuthService);
  private requestService = inject(MembershipRequestService);
  private notificationService = inject(NotificationService);
  private snackBar = inject(MatSnackBar);

  requests = signal<MembershipRequestResponse[]>([]);
  loading = signal(true);
  cancelling = signal<number | null>(null);

  private notificationSub: Subscription | null = null;

  ngOnInit(): void {
    this.querySub = this.route.queryParamMap.subscribe(() => this.loadRequests());
    this.listenForDecisions();
  }

  ngOnDestroy(): void {
    this.querySub?.unsubscribe();
    this.notificationSub?.unsubscribe();
  }

  loadRequests(): void {
    this.loading.set(true);
    this.requestService.getMyRequests().subscribe({
      next: (reqs) => {
        const selectedId = Number(this.route.snapshot.queryParamMap.get('request'));
        this.requests.set(selectedId ? reqs.filter(req => req.id === selectedId) : reqs);
        this.loading.set(false);

        // If user now has memberships (accepted elsewhere), redirect to dashboard
        if (!selectedId && this.authService.hasMemberships()) {
          this.router.navigate(['/dashboard']);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  cancelRequest(requestId: number): void {
    this.cancelling.set(requestId);
    this.requestService.cancelRequest(requestId).subscribe({
      next: () => {
        this.requests.update((list) => list.filter((r) => r.id !== requestId));
        this.cancelling.set(null);
        this.snackBar.open('Solicitud cancelada', 'Cerrar', { duration: 2000 });
      },
      error: () => {
        this.cancelling.set(null);
        this.snackBar.open('Error al cancelar la solicitud', 'Cerrar', {
          duration: 3000,
        });
      },
    });
  }

  logout(): void {
    this.authService.logout();
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      accepted: 'Aceptada',
      rejected: 'Rechazada',
    };
    return labels[status] ?? status;
  }

  statusClass(status: string): string {
    const classes: Record<string, string> = {
      pending: 'status-pending',
      accepted: 'status-accepted',
      rejected: 'status-rejected',
    };
    return classes[status] ?? '';
  }

  private listenForDecisions(): void {
    // When a membership_request_accepted notification arrives via WebSocket,
    // reload and redirect to dashboard
    this.notificationSub = this.notificationService.notificationReceived$.subscribe(
      (notification: NotificationResponse) => {
        if (
          notification?.event_type === 'membership_request_accepted'
        ) {
          this.snackBar.open(
            '¡Tu solicitud ha sido aceptada! Redirigiendo...',
            'Cerrar',
            { duration: 3000 }
          );
          // Re-validate to load memberships, then navigate
          this.authService.checkAuth().subscribe(() => {
            this.router.navigate(['/dashboard']);
          });
        } else if (notification?.event_type === 'membership_request_rejected') {
          this.loadRequests();
        }
      }
    );
  }
}
