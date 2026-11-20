import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { EntitiesService } from '../entities/entities.service';
import { AuthService } from '../auth/auth.service';
import { environment } from '../../environments/environment';

interface Counts {
  registered: number;
  under_30: number;
  incomplete: number;
  active_30_days: number;
}
interface AssociationCounts extends Counts {
  entity_id: number;
  entity_name: string;
}
interface Statistics {
  entity_id: number;
  entity_name: string;
  period_days: number;
  totals: Counts;
  associations: AssociationCounts[];
}
interface AdminEntity { id: number; name: string; }

@Component({
  selector: 'app-member-stats',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="statistics-page">
      <header class="page-header">
        <div>
          <h1>Estadísticas de socios</h1>
          <p>Resumen de las asociaciones que administras. Los accesos incluyen web y aplicación móvil.</p>
        </div>
        <div class="actions">
          <label for="stats-entity">Entidad</label>
          <select id="stats-entity" [ngModel]="selectedEntityId()" (ngModelChange)="selectEntity(+$event)">
            @for (entity of adminEntities(); track entity.id) {
              <option [ngValue]="entity.id">{{ entity.name }}</option>
            }
          </select>
          <button type="button" (click)="refresh()" [disabled]="loading()">
            <mat-icon aria-hidden="true">refresh</mat-icon> Actualizar
          </button>
        </div>
      </header>

      @if (loading()) {
        <p role="status">Cargando estadísticas…</p>
      } @else if (error()) {
        <p class="error" role="alert">{{ error() }}</p>
      } @else if (stats(); as data) {
        <div class="stat-grid">
          <article class="stat-card"><span>Socios registrados</span><strong>{{ data.totals.registered }}</strong></article>
          <article class="stat-card"><span>Jóvenes (menores de 30)</span><strong>{{ data.totals.under_30 }}</strong></article>
          <article class="stat-card"><span>Fichas por revisar</span><strong>{{ data.totals.incomplete }}</strong></article>
          <article class="stat-card"><span>Accedieron en 30 días</span><strong>{{ data.totals.active_30_days }}</strong></article>
        </div>
        <p class="note">Los totales cuentan personas distintas, aunque pertenezcan a varias asociaciones.
          Las fichas por revisar utilizan el mismo criterio que la revisión de usuarios.</p>

        @if (data.associations.length > 1) {
          <h2>Desglose por asociación local</h2>
          <div class="table-scroll">
            <table>
              <thead><tr>
                <th scope="col">Asociación</th>
                <th scope="col">Registrados</th>
                <th scope="col">Menores de 30</th>
                <th scope="col">Datos incompletos</th>
                <th scope="col">Acceso últimos 30 días</th>
              </tr></thead>
              <tbody>
                @for (row of data.associations; track row.entity_id) {
                  <tr>
                    <th scope="row">{{ row.entity_name }}</th>
                    <td>{{ row.registered }}</td>
                    <td>{{ row.under_30 }}</td>
                    <td>{{ row.incomplete }}</td>
                    <td>{{ row.active_30_days }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
        <p class="note">Periodo de actividad: últimos {{ data.period_days }} días.</p>
      }
    </section>
  `,
  styles: [`
    .statistics-page { padding: 24px; max-width: 1400px; margin: auto; color: #253450; }
    .page-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: 20px; margin-bottom: 24px; }
    h1 { margin: 0 0 8px; font-size: 1.75rem; } h2 { margin: 30px 0 14px; font-size: 1.3rem; }
    p { margin: 0; line-height: 1.5; } .actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
    select, button { border: 1px solid #c6cbd5; border-radius: 9px; padding: 10px; background: #fff; color: inherit; font: inherit; }
    button { display: flex; align-items: center; gap: 5px; cursor: pointer; }
    button:disabled { opacity: .5; cursor: default; }
    .stat-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 14px; }
    .stat-card { background: #fff; border: 1px solid #e4e7ed; border-radius: 14px; padding: 22px; display: flex; flex-direction: column; gap: 12px; }
    .stat-card span { color: #56657f; font-weight: 600; }
    .stat-card strong { color: #3d4e7c; font-size: clamp(1.8rem,4vw,3rem); }
    .table-scroll { overflow-x: auto; border: 1px solid #e4e7ed; border-radius: 12px; }
    table { width: 100%; border-collapse: collapse; background: white; text-align: left; min-width: 680px; }
    th, td { padding: 15px 17px; border-bottom: 1px solid #e4e7ed; }
    td:not(:first-child), thead th:not(:first-child) { text-align: right; font-variant-numeric: tabular-nums; }
    thead { background: #f0f2f7; } tr:last-child th, tr:last-child td { border-bottom: 0; }
    .note { color: #687487; font-size: .875rem; margin: 16px 0; } .error { color: #9d2222; }
    @media(max-width: 800px) { .statistics-page { padding: 16px; } .stat-grid { grid-template-columns: repeat(2,minmax(0,1fr)); } }
    @media(max-width: 430px) { .stat-grid { grid-template-columns: 1fr 1fr; gap: 8px; } .stat-card { padding: 13px; } .stat-card span { font-size: .8rem; } }
  `]
})
export class MemberStatsComponent implements OnInit {
  private http = inject(HttpClient);
  private entities = inject(EntitiesService);
  private auth = inject(AuthService);
  adminEntities = signal<AdminEntity[]>([]);
  selectedEntityId = signal<number | null>(null);
  stats = signal<Statistics | null>(null);
  loading = signal(true);
  error = signal('');
  selected = computed(() => this.adminEntities().find(e => e.id === this.selectedEntityId()));

  ngOnInit(): void {
    this.entities.getAdminEntities().subscribe({
      next: entities => {
        this.adminEntities.set(entities);
        const preferred = this.auth.getCurrentMembership()?.entity_id;
        const first = entities.find(e => e.id === preferred) ?? entities[0];
        if (first) this.selectEntity(first.id);
        else { this.error.set('No administras ninguna entidad.'); this.loading.set(false); }
      },
      error: () => { this.error.set('No se pudo cargar la lista de entidades.'); this.loading.set(false); }
    });
  }

  selectEntity(id: number): void {
    if (!this.adminEntities().some(entity => entity.id === id)) return;
    this.selectedEntityId.set(id);
    this.refresh();
  }

  refresh(): void {
    const id = this.selectedEntityId();
    if (!id) return;
    this.loading.set(true);
    this.stats.set(null);
    this.error.set('');
    this.http.get<Statistics>(`${environment.apiUrl}/member-stats/entity/${id}`).subscribe({
      next: data => { this.stats.set(data); this.loading.set(false); },
      error: e => {
        this.error.set(e.status === 403
          ? 'Las estadísticas no están habilitadas para esta entidad o no tienes acceso.'
          : 'No se pudieron cargar las estadísticas.');
        this.loading.set(false);
      }
    });
  }
}
