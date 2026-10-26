import { Component, OnInit, signal, inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';

import { MembershipRequestService } from '../membership-request.service';
import { MembershipRequestResponse } from '../../models/user.model';
import { RejectReasonDialogComponent } from './reject-reason-dialog.component';

@Component({
  selector: 'app-membership-requests-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    MatChipsModule,
  ],
  templateUrl: './membership-requests-list.component.html',
  styleUrl: './membership-requests-list.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MembershipRequestsListComponent implements OnInit {
  private requestService = inject(MembershipRequestService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  requests = signal<MembershipRequestResponse[]>([]);
  loading = signal(true);
  statusFilter = signal<string>('pending');
  processingId = signal<number | null>(null);

  displayedColumns = ['user', 'entity', 'date', 'message', 'actions'];

  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests(): void {
    this.loading.set(true);
    this.requestService.getRequests(undefined, this.statusFilter() || undefined).subscribe({
      next: (reqs) => {
        this.requests.set(reqs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onFilterChange(status: string): void {
    this.statusFilter.set(status);
    this.loadRequests();
  }

  accept(req: MembershipRequestResponse): void {
    this.processingId.set(req.id);
    this.requestService.acceptRequest(req.id).subscribe({
      next: () => {
        this.requests.update((list) =>
          list.map((r) => (r.id === req.id ? { ...r, status: 'accepted' as const } : r))
        );
        if (this.statusFilter() === 'pending') {
          this.requests.update((list) => list.filter((r) => r.id !== req.id));
        }
        this.processingId.set(null);
        this.snackBar.open(
          `${req.user?.name} ${req.user?.surname} ha sido aceptado/a`,
          'Cerrar',
          { duration: 3000 }
        );
      },
      error: () => {
        this.processingId.set(null);
        this.snackBar.open('Error al aceptar la solicitud', 'Cerrar', {
          duration: 3000,
        });
      },
    });
  }

  openRejectDialog(req: MembershipRequestResponse): void {
    const dialogRef = this.dialog.open(RejectReasonDialogComponent, {
      width: '400px',
      data: { userName: `${req.user?.name} ${req.user?.surname}` },
    });

    dialogRef.afterClosed().subscribe((reason: string | undefined) => {
      if (reason !== undefined) {
        // undefined = dialog cancelled; null/empty = reject without reason
        this.reject(req, reason || undefined);
      }
    });
  }

  private reject(req: MembershipRequestResponse, reason?: string): void {
    this.processingId.set(req.id);
    this.requestService.rejectRequest(req.id, reason).subscribe({
      next: () => {
        this.requests.update((list) =>
          list.map((r) => (r.id === req.id ? { ...r, status: 'rejected' as const } : r))
        );
        if (this.statusFilter() === 'pending') {
          this.requests.update((list) => list.filter((r) => r.id !== req.id));
        }
        this.processingId.set(null);
        this.snackBar.open(
          `Solicitud de ${req.user?.name} rechazada`,
          'Cerrar',
          { duration: 3000 }
        );
      },
      error: () => {
        this.processingId.set(null);
        this.snackBar.open('Error al rechazar la solicitud', 'Cerrar', {
          duration: 3000,
        });
      },
    });
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      accepted: 'Aceptada',
      rejected: 'Rechazada',
    };
    return labels[status] ?? status;
  }
}
