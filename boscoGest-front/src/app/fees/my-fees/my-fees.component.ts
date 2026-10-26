import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FeesService } from '../fees.service';
import { SubmitProofDialogComponent } from '../submit-proof-dialog/submit-proof-dialog.component';
import { FeeAssignmentResponse, FEE_STATUS_LABELS, FEE_STATUS_COLORS, FeeStatus, FeePeriodicity, FEE_PERIODICITY_LABELS } from '../../models/user.model';

@Component({
  selector: 'app-my-fees',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatButtonModule,
    MatDialogModule,
    MatTooltipModule,
  ],
  templateUrl: './my-fees.component.html',
  styleUrl: './my-fees.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MyFeesComponent implements OnInit {
  assignments = signal<FeeAssignmentResponse[]>([]);
  loading = signal(true);

  constructor(
    private feesService: FeesService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.feesService.getMyAssignments().subscribe({
      next: (list) => {
        this.assignments.set(list.sort((a, b) => b.period.localeCompare(a.period)));
        this.loading.set(false);
      },
      error: () => {
        this.snackBar.open('Error al cargar tus cuotas', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      }
    });
  }

  /**
   * Whether the member can act on this charge.
   *
   * Anything already settled — paid, cancelled, exempt — is not theirs to
   * touch. A charge whose receipt is under review is not either: sending
   * another would just add noise for the treasurer.
   */
  canSendProof(assignment: FeeAssignmentResponse): boolean {
    return assignment.status === 'pending' || assignment.status === 'overdue';
  }

  openProofDialog(assignment: FeeAssignmentResponse): void {
    const dialogRef = this.dialog.open(SubmitProofDialogComponent, {
      width: '34rem',
      maxWidth: '92vw',
      autoFocus: false,
      data: { assignment },
    });

    dialogRef.afterClosed().subscribe((updated: FeeAssignmentResponse | undefined) => {
      if (!updated) {
        return;
      }
      this.assignments.update((list) =>
        list.map((a) => (a.id === updated.id ? updated : a))
      );
      this.snackBar.open(
        'Justificante enviado. Te avisaremos cuando lo revisen.',
        'Cerrar',
        { duration: 5000, panelClass: 'success-snackbar' }
      );
    });
  }

  viewProof(assignment: FeeAssignmentResponse): void {
    this.feesService.getProofUrl(assignment.id).subscribe({
      next: ({ url }) => window.open(url, '_blank', 'noopener'),
      error: () =>
        this.snackBar.open('No se ha podido abrir el justificante', 'Cerrar', {
          duration: 3000,
        }),
    });
  }

  getStatusLabel(status: FeeStatus): string {
    return FEE_STATUS_LABELS[status] ?? status;
  }

  getStatusColor(status: FeeStatus): string {
    return FEE_STATUS_COLORS[status] ?? '#9e9e9e';
  }

  getPeriodicityLabel(p: FeePeriodicity): string {
    return FEE_PERIODICITY_LABELS[p] ?? p;
  }

  getStatusIcon(status: FeeStatus): string {
    switch (status) {
      case 'paid': return 'check_circle';
      case 'pending': return 'schedule';
      case 'overdue': return 'warning';
      case 'cancelled': return 'cancel';
      case 'submitted': return 'hourglass_top';
      case 'exempt': return 'volunteer_activism';
      default: return 'help';
    }
  }
}
