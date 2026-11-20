import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, ChangeDetectionStrategy, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpClient, HttpParams } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { EntitiesService } from '../entities/entities.service';
import { AuthService } from '../auth/auth.service';
import { environment } from '../../environments/environment';

type Period = 'all' | '90d' | '30d' | '7d';
type Metric = 'registered' | 'under_30' | 'incomplete' | 'active_30_days';
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
interface MemberRow { id: number; name: string; surname: string; associations: string[]; }
interface MemberPage { total: number; skip: number; limit: number; items: MemberRow[]; }
interface AdminEntity { id: number; name: string; }
interface CardDefinition { key: Metric; label: string; icon: string; }

@Component({
  selector: 'app-member-stats',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="statistics-page">
      <header class="page-header">
        <div>
          <h1>Estadísticas de socios</h1>
          <p>Selecciona un indicador para ver sus socios y acceder a sus fichas.</p>
        </div>
        <div class="actions">
          <label for="stats-entity">Entidad</label>
          <select id="stats-entity" [ngModel]="selectedEntityId()" (ngModelChange)="selectEntity(+$event)">
            @for (entity of adminEntities(); track entity.id) {
              <option [ngValue]="entity.id">{{ entity.name }}</option>
            }
          </select>
          <label for="stats-period">Periodo</label>
          <select id="stats-period" [ngModel]="period()" (ngModelChange)="setPeriod($event)">
            <option value="all">Desde siempre</option>
            <option value="90d">Últimos 3 meses</option>
            <option value="30d">Último mes</option>
            <option value="7d">Última semana</option>
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
          @for (card of cards; track card.key) {
            <button type="button" class="stat-card" [class.selected]="expandedMetric() === card.key"
                    [attr.aria-expanded]="expandedMetric() === card.key"
                    [attr.aria-controls]="'member-stats-detail'"
                    (click)="toggleMetric(card.key)">
              <span class="stat-heading"><mat-icon aria-hidden="true">{{ card.icon }}</mat-icon>{{ card.label }}</span>
              <strong>{{ data.totals[card.key] }}</strong>
              <span class="open-hint">{{ expandedMetric() === card.key ? 'Ocultar socios' : 'Ver socios' }}
                <mat-icon aria-hidden="true">{{ expandedMetric() === card.key ? 'expand_less' : 'expand_more' }}</mat-icon>
              </span>
            </button>
          }
        </div>

        @if (expandedMetric(); as metric) {
          <section class="detail-section" id="member-stats-detail" aria-live="polite">
            <div class="detail-header">
              <div>
                <h2>{{ cardLabel(metric) }} <span class="counter">({{ members().total }})</span></h2>
                <p>Selecciona un socio para ver su ficha o editar sus datos con los permisos habituales.</p>
              </div>
              @if (data.associations.length > 1) {
                <div class="filter-association">
                  <label for="stats-association">Asociación</label>
                  <select id="stats-association" [ngModel]="associationFilter()" (ngModelChange)="setAssociation($event)">
                    <option [ngValue]="null">Todas las asociaciones</option>
                    @for (association of data.associations; track association.entity_id) {
                      <option [ngValue]="association.entity_id">{{ association.entity_name }}</option>
                    }
                  </select>
                </div>
              }
            </div>
            @if (membersLoading()) {
              <p role="status">Cargando socios…</p>
            } @else if (membersError()) {
              <p class="error" role="alert">{{ membersError() }}</p>
            } @else if (members().total === 0) {
              <p>No hay socios en este indicador y periodo.</p>
            } @else {
              <div class="table-scroll">
                <table>
                  <thead><tr>
                    <th scope="col">Socio</th>
                    <th scope="col">Asociación</th>
                    <th scope="col">Acciones</th>
                  </tr></thead>
                  <tbody>
                    @for (member of members().items; track member.id) {
                      <tr>
                        <th scope="row">{{ member.name }} {{ member.surname }}</th>
                        <td>{{ member.associations.join(', ') }}</td>
                        <td class="row-actions">
                          <a [routerLink]="['/users', member.id]">Ver ficha</a>
                          @if (canEdit()) {
                            <a [routerLink]="['/users', member.id, 'edit']">Editar</a>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
              <div class="pagination">
                <span>{{ memberOffset() + 1 }}–{{ memberOffset() + members().items.length }} de {{ members().total }}</span>
                <button type="button" (click)="changePage(-1)" [disabled]="memberOffset() === 0 || membersLoading()">Anterior</button>
                <button type="button" (click)="changePage(1)"
                        [disabled]="memberOffset() + members().items.length >= members().total || membersLoading()">Siguiente</button>
              </div>
            }
          </section>
        }

        @if (data.associations.length > 1) {
          <h2>Desglose por asociación local</h2>
          <div class="table-scroll">
            <table>
              <thead><tr>
                <th scope="col">Asociación</th>
                <th scope="col">Registrados</th>
                <th scope="col">Menores de 30</th>
                <th scope="col">Datos incompletos</th>
                <th scope="col">Con acceso</th>
              </tr></thead>
              <tbody>
                @for (row of data.associations; track row.entity_id) {
                  <tr>
                    <th scope="row">{{ row.entity_name }}</th>
                    @for (card of cards; track card.key) {
                      <td class="number">
                        <button type="button" class="number-link"
                                [attr.aria-label]="card.label + ' de ' + row.entity_name"
                                (click)="selectBreakdown(card.key, row.entity_id)">{{ row[card.key] }}</button>
                      </td>
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
        <p class="note">Para los tres primeros indicadores, el periodo filtra por fecha de registro.
          «Con acceso» muestra socios que han iniciado o renovado sesión durante el periodo.
          Cada persona se cuenta una sola vez en los totales.</p>
      }
    </section>
  `,
  styles: [`
    .statistics-page { padding: 24px; max-width: 1400px; margin: auto; color: #253450; }
    .page-header, .detail-header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: 20px; margin-bottom: 24px; }
    h1 { margin: 0 0 8px; font-size: 1.75rem; } h2 { margin: 28px 0 12px; font-size: 1.3rem; }
    p { margin: 0; line-height: 1.5; } .actions, .filter-association { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
    select, button:not(.stat-card):not(.number-link) { border: 1px solid #c6cbd5; border-radius: 9px; padding: 10px; background: #fff; color: inherit; font: inherit; }
    button { cursor: pointer; } button:disabled { opacity: .5; cursor: default; }
    .stat-grid { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 14px; }
    .stat-card { text-align: left; color: #253450; background: #fff; border: 2px solid #e4e7ed; border-radius: 14px; padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .stat-card:hover, .stat-card.selected { border-color: #3d4e7c; }
    .stat-heading { display: flex; align-items: center; gap: 8px; color: #56657f; font-weight: 600; }
    .stat-card strong { color: #3d4e7c; font-size: clamp(1.8rem,4vw,3rem); }
    .open-hint { display: flex; align-items: center; gap: 4px; font-size: .85rem; color: #3d4e7c; }
    .detail-section { border: 1px solid #dce1ed; border-radius: 14px; padding: 20px; margin-top: 22px; background: #fff; }
    .detail-header h2 { margin: 0 0 8px; } .counter { color: #687487; font-weight: 400; }
    .table-scroll { overflow-x: auto; border: 1px solid #e4e7ed; border-radius: 12px; }
    table { width: 100%; border-collapse: collapse; background: white; text-align: left; min-width: 620px; }
    th, td { padding: 14px 17px; border-bottom: 1px solid #e4e7ed; }
    .number { text-align: right; font-variant-numeric: tabular-nums; }
    .number-link { border: 0; background: none; color: #31518c; font: inherit; text-decoration: underline; padding: 4px; }
    thead { background: #f0f2f7; } tr:last-child th, tr:last-child td { border-bottom: 0; }
    .row-actions { display: flex; flex-wrap: wrap; gap: 14px; white-space: nowrap; }
    a { color: #31518c; font-weight: 600; } .pagination { display: flex; justify-content: end; align-items: center; flex-wrap: wrap; gap: 12px; margin-top: 14px; }
    .note { color: #687487; font-size: .875rem; margin: 16px 0; } .error { color: #9d2222; }
    @media(max-width: 800px) { .statistics-page { padding: 16px; } .stat-grid { grid-template-columns: repeat(2,minmax(0,1fr)); } }
    @media(max-width: 430px) { .stat-grid { gap: 8px; } .stat-card { padding: 13px; } .stat-heading { font-size: .85rem; } .detail-section { padding: 12px; } }
  `]
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
  memberOffset = signal(0);
  members = signal<MemberPage>({total: 0, skip: 0, limit: 25, items: []});
  membersLoading = signal(false);
  membersError = signal('');
  canEdit = computed(() => this.auth.canPerform('users', 'update'));
  private requestId = 0;
  private detailRequestId = 0;

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

  cardLabel(key: Metric): string {
    return this.cards.find(card => card.key === key)?.label ?? key;
  }

  selectEntity(id: number): void {
    if (!this.adminEntities().some(entity => entity.id === id)) return;
    this.selectedEntityId.set(id);
    this.expandedMetric.set(null);
    this.associationFilter.set(null);
    this.refresh();
  }

  setPeriod(value: Period): void {
    if (!['all', '90d', '30d', '7d'].includes(value)) return;
    this.period.set(value);
    this.refresh();
  }

  refresh(): void {
    const id = this.selectedEntityId();
    if (!id) return;
    const requestId = ++this.requestId;
    ++this.detailRequestId;
    this.loading.set(true);
    this.stats.set(null);
    this.members.set({total: 0, skip: 0, limit: 25, items: []});
    this.error.set('');
    this.http.get<Statistics>(`${environment.apiUrl}/member-stats/entity/${id}`, {
      params: {period: this.period()}
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: data => {
        if (requestId !== this.requestId) return;
        this.stats.set(data); this.loading.set(false);
        if (this.expandedMetric()) this.loadMembers();
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
    if (this.expandedMetric() === metric) {
      this.expandedMetric.set(null);
      ++this.detailRequestId;
      return;
    }
    this.expandedMetric.set(metric);
    this.associationFilter.set(null);
    this.memberOffset.set(0);
    this.loadMembers();
  }

  selectBreakdown(metric: Metric, id: number): void {
    this.expandedMetric.set(metric);
    this.associationFilter.set(id);
    this.memberOffset.set(0);
    this.loadMembers();
  }

  setAssociation(value: number | null): void {
    this.associationFilter.set(value === null ? null : Number(value));
    this.memberOffset.set(0);
    this.loadMembers();
  }

  changePage(direction: number): void {
    const next = this.memberOffset() + direction * 25;
    if (next < 0 || next >= this.members().total) return;
    this.memberOffset.set(next);
    this.loadMembers();
  }

  loadMembers(): void {
    const id = this.selectedEntityId();
    const metric = this.expandedMetric();
    if (!id || !metric) return;
    const requestId = ++this.detailRequestId;
    this.membersLoading.set(true);
    this.membersError.set('');
    let params = new HttpParams()
      .set('period', this.period())
      .set('metric', metric)
      .set('skip', this.memberOffset())
      .set('limit', 25);
    if (this.associationFilter() !== null) {
      params = params.set('association_id', this.associationFilter()!);
    }
    this.http.get<MemberPage>(`${environment.apiUrl}/member-stats/entity/${id}/members`, {params})
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: data => {
          if (requestId !== this.detailRequestId) return;
          this.members.set(data);
          this.membersLoading.set(false);
        },
        error: () => {
          if (requestId !== this.detailRequestId) return;
          this.membersError.set('No se pudo cargar el desglose de socios.');
          this.membersLoading.set(false);
        },
      });
  }
}
