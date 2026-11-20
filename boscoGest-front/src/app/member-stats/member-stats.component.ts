import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, ChangeDetectionStrategy, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { EntitiesService } from '../entities/entities.service';
import { AuthService } from '../auth/auth.service';
import { UsersListComponent, StatsTableFilter } from '../users/users-list/users-list.component';
import { environment } from '../../environments/environment';

type Period = 'all' | '90d' | '30d' | '7d';
type Metric = StatsTableFilter['metric'];
type Counts = Record<Metric, number>;
interface AssociationCounts extends Counts { entity_id: number; entity_name: string; }
interface Statistics {
  entity_id: number;
  entity_name: string;
  period: Period;
  period_days: number | null;
  totals: Counts;
  associations: AssociationCounts[];
}
interface AdminEntity { id: number; name: string; }
interface CardDefinition { key: Metric; label: string; icon: string; }

@Component({
  selector: 'app-member-stats',
  standalone: true,
  imports: [
    CommonModule, MatCardModule, MatIconModule, MatSelectModule,
    MatFormFieldModule, MatButtonModule, UsersListComponent
  ],
  // Share the real Admin Usuarios styles. No duplicated palette or font.
  styleUrls: ['../users/users-list/users-list.component.css', './member-stats.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="users-container">
      <h1 class="page-title">Estadísticas de socios</h1>
      <mat-card class="users-card">
        <mat-card-header>
          <mat-card-title class="section-title">
            <mat-icon class="title-icon" aria-hidden="true">insights</mat-icon>
            Resumen de socios
          </mat-card-title>
        </mat-card-header>
        <mat-card-content class="card-content">
          <div class="stats-filters">
            <mat-form-field appearance="outline">
              <mat-label>Entidad</mat-label>
              <mat-select [value]="selectedEntityId()" (selectionChange)="selectEntity($event.value)">
                @for (entity of adminEntities(); track entity.id) {
                  <mat-option [value]="entity.id">{{ entity.name }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Periodo</mat-label>
              <mat-select [value]="period()" (selectionChange)="setPeriod($event.value)">
                <mat-option value="all">Desde siempre</mat-option>
                <mat-option value="90d">Últimos 3 meses</mat-option>
                <mat-option value="30d">Último mes</mat-option>
                <mat-option value="7d">Última semana</mat-option>
              </mat-select>
            </mat-form-field>
            <button mat-stroked-button type="button" (click)="refresh()" [disabled]="loading()">
              <mat-icon aria-hidden="true">refresh</mat-icon> Actualizar
            </button>
          </div>

          @if (loading()) {
            <div class="loading-container" role="status">Cargando estadísticas…</div>
          } @else if (error()) {
            <p class="empty-state" role="alert">{{ error() }}</p>
          } @else if (stats(); as data) {
            <div class="stats-grid">
              @for (card of cards; track card.key) {
                <mat-card class="stat-metric" [class.metric-expanded]="expandedMetric() === card.key">
                  <button type="button" class="metric-button"
                          [attr.aria-expanded]="expandedMetric() === card.key"
                          [attr.aria-controls]="'stats-users-detail'"
                          (click)="toggleMetric(card.key)">
                    <span class="metric-label">
                      <mat-icon aria-hidden="true">{{ card.icon }}</mat-icon>
                      {{ card.label }}
                    </span>
                    <span class="metric-value">{{ data.totals[card.key] }}</span>
                    <span class="metric-toggle">
                      {{ expandedMetric() === card.key ? 'Ocultar socios' : 'Desglosar socios' }}
                      <mat-icon aria-hidden="true">{{ expandedMetric() === card.key ? 'keyboard_arrow_up' : 'keyboard_arrow_down' }}</mat-icon>
                    </span>
                  </button>
                </mat-card>
              }
            </div>

            @if (expandedMetric(); as metric) {
              <div id="stats-users-detail" class="stats-details">
                <div class="detail-heading">
                  <h2 class="section-title">{{ cardLabel(metric) }}</h2>
                  @if (data.associations.length > 1) {
                    <mat-form-field appearance="outline">
                      <mat-label>Asociación</mat-label>
                      <mat-select [value]="associationFilter()" (selectionChange)="setAssociation($event.value)">
                        <mat-option [value]="null">Todas las asociaciones</mat-option>
                        @for (association of data.associations; track association.entity_id) {
                          <mat-option [value]="association.entity_id">{{ association.entity_name }}</mat-option>
                        }
                      </mat-select>
                    </mat-form-field>
                  }
                </div>
                <!-- Identical Admin Usuarios component: columns, controls and actions. -->
                @if (tableFilter(); as filter) {
                  <app-users-list [statsFilter]="filter"></app-users-list>
                }
              </div>
            }

            @if (data.associations.length > 1) {
              <h2 class="section-title association-title">Desglose por asociación local</h2>
              <div class="table-container">
                <table class="users-table">
                  <thead>
                    <tr>
                      <th class="table-header">Asociación</th>
                      @for (card of cards; track card.key) {
                        <th class="table-header">{{ card.label }}</th>
                      }
                    </tr>
                  </thead>
                  <tbody>
                    @for (row of data.associations; track row.entity_id) {
                      <tr class="table-row">
                        <th class="table-cell">{{ row.entity_name }}</th>
                        @for (card of cards; track card.key) {
                          <td class="table-cell">
                            <button mat-button type="button" class="association-count"
                                    [attr.aria-label]="card.label + ' de ' + row.entity_name"
                                    (click)="selectBreakdown(card.key, row.entity_id)">
                              {{ row[card.key] }}
                              <mat-icon aria-hidden="true">keyboard_arrow_down</mat-icon>
                            </button>
                          </td>
                        }
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
            <p class="stats-explanation">
              Registrados, jóvenes y fichas incompletas: socios inscritos durante el periodo elegido.
              Accesos: socios que iniciaron o renovaron sesión en ese intervalo.
              Una persona se cuenta una sola vez en los totales.
            </p>
          }
        </mat-card-content>
      </mat-card>
    </div>
  `
})
export class MemberStatsComponent implements OnInit {
  private http = inject(HttpClient);
  private entities = inject(EntitiesService);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);
  readonly cards: CardDefinition[] = [
    {key: 'registered', label: 'Socios registrados', icon: 'groups'},
    {key: 'under_30', label: 'Jóvenes (menores de 30)', icon: 'person'},
    {key: 'incomplete', label: 'Datos incompletos', icon: 'error_outline'},
    {key: 'active_30_days', label: 'Con acceso en el periodo', icon: 'login'},
  ];
  adminEntities = signal<AdminEntity[]>([]);
  selectedEntityId = signal<number | null>(null);
  period = signal<Period>('30d');
  stats = signal<Statistics | null>(null);
  loading = signal(true);
  error = signal('');
  expandedMetric = signal<Metric | null>(null);
  associationFilter = signal<number | null>(null);
  tableFilter = computed<StatsTableFilter | null>(() => {
    const entityId = this.selectedEntityId();
    const metric = this.expandedMetric();
    return entityId && metric ? {
      entityId, metric, period: this.period(), associationId: this.associationFilter()
    } : null;
  });
  private requestId = 0;

  ngOnInit(): void {
    this.entities.getAdminEntities().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
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
  cardLabel(metric: Metric): string {
    return this.cards.find(card => card.key === metric)?.label ?? metric;
  }
  selectEntity(id: number): void {
    if (!this.adminEntities().some(e => e.id === id)) return;
    this.selectedEntityId.set(id);
    this.expandedMetric.set(null);
    this.associationFilter.set(null);
    this.refresh();
  }
  setPeriod(period: Period): void {
    if (!['all', '90d', '30d', '7d'].includes(period)) return;
    this.period.set(period);
    this.refresh();
  }
  refresh(): void {
    const id = this.selectedEntityId();
    if (!id) return;
    const requestId = ++this.requestId;
    this.loading.set(true);
    this.error.set('');
    this.http.get<Statistics>(`${environment.apiUrl}/member-stats/entity/${id}`, {
      params: {period: this.period()}
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: stats => {
        if (requestId !== this.requestId) return;
        this.stats.set(stats);
        this.loading.set(false);
      },
      error: e => {
        if (requestId !== this.requestId) return;
        this.error.set(e.status === 403
          ? 'Las estadísticas no están habilitadas para esta entidad o no tienes acceso.'
          : 'No se pudieron cargar las estadísticas.');
        this.loading.set(false);
      }
    });
  }
  toggleMetric(metric: Metric): void {
    const closed = this.expandedMetric() === metric;
    this.expandedMetric.set(closed ? null : metric);
    this.associationFilter.set(null);
  }
  selectBreakdown(metric: Metric, entityId: number): void {
    this.expandedMetric.set(metric);
    this.associationFilter.set(entityId);
  }
  setAssociation(id: number | null): void {
    this.associationFilter.set(id);
  }
}
