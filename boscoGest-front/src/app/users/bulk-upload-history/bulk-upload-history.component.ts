import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { environment } from '../../../environments/environment';
import { BulkUploadJob } from '../user-import/user-import.component';

@Component({
  selector: 'app-bulk-upload-history',
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  templateUrl: './bulk-upload-history.component.html',
  styleUrl: './bulk-upload-history.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class BulkUploadHistoryComponent implements OnInit {
  jobs = signal<BulkUploadJob[]>([]);
  isLoading = signal<boolean>(true);

  displayedColumns = ['id', 'csv_filename', 'status', 'total_rows', 'successful', 'failed', 'created_at', 'actions'];

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.loadJobs();
  }

  loadJobs(): void {
    this.isLoading.set(true);
    this.http.get<BulkUploadJob[]>(`${environment.apiUrl}/users/bulk-upload/jobs`).subscribe({
      next: (jobs) => {
        this.jobs.set(jobs);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
        this.snackBar.open('Error al cargar el historial', 'Cerrar', {
          duration: 3000,
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  openDetail(job: BulkUploadJob): void {
    // Una vista, no un modal: el detalle es una tabla que se recorre y se
    // comparte, y ahora tiene dirección propia.
    this.router.navigate(['/users/import/history', job.id]);
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      running: 'En curso',
      completed: 'Completado',
      failed: 'Fallido',
    };
    return labels[status] ?? status;
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('es-ES', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}
