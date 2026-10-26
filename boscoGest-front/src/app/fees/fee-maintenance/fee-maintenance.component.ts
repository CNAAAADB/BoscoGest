import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FeesService } from '../fees.service';
import { FeeMaintenanceRun } from '../../models/user.model';

@Component({
  selector: 'app-fee-maintenance',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './fee-maintenance.component.html',
  styleUrl: './fee-maintenance.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FeeMaintenanceComponent implements OnInit {
  runs = signal<FeeMaintenanceRun[]>([]);
  loading = signal(true);
  running = signal(false);

  constructor(private feesService: FeesService, private snackBar: MatSnackBar) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.feesService.getMaintenanceRuns().subscribe({
      next: (runs) => { this.runs.set(runs); this.loading.set(false); },
      error: () => {
        this.snackBar.open('Error al cargar las ejecuciones', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      },
    });
  }

  runNow(): void {
    this.running.set(true);
    this.feesService.runMaintenance().subscribe({
      next: (run) => {
        this.snackBar.open(
          `Ejecución completada: ${run.overdue_count} vencidas, ${run.reminded_count} avisos, ${run.renewed_count} renovadas`,
          'Cerrar', { duration: 5000 });
        this.running.set(false);
        this.load();
      },
      error: () => {
        this.snackBar.open('Error al ejecutar el mantenimiento', 'Cerrar', { duration: 3000 });
        this.running.set(false);
      },
    });
  }

  durationSeconds(run: FeeMaintenanceRun): number | null {
    if (!run.finished_at) return null;
    return Math.max(0, (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000);
  }

  prettyDetails(run: FeeMaintenanceRun): string {
    return JSON.stringify(run.details ?? {}, null, 2);
  }
}
