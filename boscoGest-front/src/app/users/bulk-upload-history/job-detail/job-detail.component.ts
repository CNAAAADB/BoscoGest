import { Component, OnInit, signal, computed, inject, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { environment } from '../../../../environments/environment';
import { BulkUploadJob } from '../../user-import/user-import.component';

/**
 * One import, on its own page.
 *
 * It used to be a dialog, which suited it badly: the interesting content is a
 * table of hundreds of rows that people scroll, compare and come back to, and
 * a dialog gives it a cramped box, no address to return to and nothing to send
 * anyone. As a route it can be bookmarked, shared with whoever prepared the
 * file, and reloaded straight from the URL — which is why the job is fetched
 * here by id rather than handed in.
 */
@Component({
  selector: 'app-job-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTableModule,
    MatTabsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './job-detail.component.html',
  styleUrl: './job-detail.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JobDetailComponent implements OnInit {
  private http = inject(HttpClient);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private snackBar = inject(MatSnackBar);

  job = signal<BulkUploadJob | null>(null);
  loading = signal(true);

  successCols = ['id', 'name', 'email', 'entity_id'];
  errorCols = ['row', 'email', 'error'];

  /** Share of rows that went in, for the bar under the summary. */
  successRate = computed(() => {
    const j = this.job();
    if (!j || !j.total_rows) {
      return 0;
    }
    return Math.round((j.successful / j.total_rows) * 100);
  });

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isFinite(id) || id <= 0) {
      // A hand-typed or truncated URL: go back rather than ask the API about
      // a job that cannot exist.
      this.router.navigate(['/users/import/history']);
      return;
    }
    this.load(id);
  }

  private load(id: number): void {
    this.http
      .get<BulkUploadJob>(`${environment.apiUrl}/users/bulk-upload/${id}`)
      .subscribe({
        next: (job) => {
          this.job.set(job);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.snackBar.open('No se ha encontrado esa importación', 'Cerrar', {
            duration: 4000,
            panelClass: ['error-snackbar'],
          });
          this.router.navigate(['/users/import/history']);
        },
      });
  }

  /**
   * Download the failed rows so they can be worked through in a spreadsheet.
   * Hundreds of errors are unreadable on screen, and this is the same shape
   * the pre-import check produces.
   */
  downloadErrors(): void {
    const j = this.job();
    if (!j || !j.errors.length) {
      return;
    }

    const filas = [
      ['fila', 'email', 'error'],
      ...j.errors.map((e: any) => [
        String(e.row),
        e.data?.email ?? '',
        e.error ?? '',
      ]),
    ];
    // The BOM is what makes Excel read UTF-8 without mangling the accents.
    const csv =
      '﻿' +
      filas
        .map((f) => f.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
        .join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `errores_importacion_${j.id}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
}
