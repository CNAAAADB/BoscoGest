import { ChangeDetectionStrategy, Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import { UsersService } from '../users.service';
import { BoardPosition, BoardPositionEntity, BoardRoleCode } from '../../models/user.model';

@Component({
  selector: 'app-board-positions',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatCardModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatSelectModule, MatInputModule, MatChipsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-card class="board-card">
      <mat-card-header>
        <mat-card-title class="board-title">
          <mat-icon aria-hidden="true">account_tree</mat-icon>
          Cargos en juntas
        </mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <p class="board-help">
          Etiquetas vinculadas a cada entidad. No modifican los permisos de usuario.
        </p>

        @if (loading()) {
          <p role="status">Cargando cargos…</p>
        } @else {
          @if (positions().length) {
            <div class="board-list">
              @for (position of positions(); track position.id) {
                <div class="board-entry">
                  <div class="board-entry-info">
                    <mat-chip>
                      <mat-icon matChipAvatar aria-hidden="true">badge</mat-icon>
                      {{ position.title }}
                    </mat-chip>
                    <span>{{ position.entity_name }}</span>
                  </div>
                  @if (canRemove(position)) {
                    <button mat-icon-button type="button"
                            [disabled]="saving()"
                            (click)="remove(position)"
                            [attr.aria-label]="'Retirar ' + position.title + ' en ' + position.entity_name"
                            matTooltip="Retirar cargo">
                      <mat-icon aria-hidden="true">delete_outline</mat-icon>
                    </button>
                  }
                </div>
              }
            </div>
          } @else {
            <p class="board-empty">No hay cargos de junta asignados en las entidades visibles.</p>
          }

          @if (assignableEntities().length) {
            <div class="board-editor">
              <h3>Asignar cargo</h3>
              <div class="board-fields">
                <mat-form-field appearance="outline">
                  <mat-label>Entidad del usuario</mat-label>
                  <mat-select [ngModel]="entityId()" (ngModelChange)="entityId.set($event)">
                    @for (entity of assignableEntities(); track entity.id) {
                      <mat-option [value]="entity.id">{{ entity.name }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Cargo</mat-label>
                  <mat-select [ngModel]="role()" (ngModelChange)="role.set($event)">
                    @for (option of roleOptions; track option.code) {
                      <mat-option [value]="option.code">{{ option.label }}</mat-option>
                    }
                  </mat-select>
                </mat-form-field>
                @if (role() === 'otro') {
                  <mat-form-field appearance="outline">
                    <mat-label>Nombre del cargo personalizado</mat-label>
                    <input matInput [ngModel]="customTitle()"
                           (ngModelChange)="customTitle.set($event)"
                           maxlength="80" placeholder="Por ejemplo, Vocal de formación">
                  </mat-form-field>
                }
              </div>
              <button mat-raised-button color="primary" type="button"
                      (click)="add()" [disabled]="!canSubmit() || saving()">
                <mat-icon aria-hidden="true">add</mat-icon>
                Añadir cargo
              </button>
            </div>
          }
        }
        @if (error()) {
          <p class="board-error" role="alert">{{ error() }}</p>
        }
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    .board-card { margin-top: 1.5rem; }
    .board-title { display: flex; align-items: center; gap: .65rem; }
    .board-title mat-icon { color: var(--primary-color, currentColor); }
    .board-help { margin: .75rem 0 1rem; opacity: .8; }
    .board-list { display: flex; flex-direction: column; gap: .5rem; margin-bottom: 1rem; }
    .board-entry { border-bottom: 1px solid var(--border-color, #e7e8ea);
      display: flex; justify-content: space-between; align-items: center; gap: .5rem;
      padding: .5rem 0; }
    .board-entry-info { display: flex; align-items: center; gap: .8rem; flex-wrap: wrap; }
    .board-empty { opacity: .75; }
    .board-editor { padding-top: 1rem; margin-top: 1rem;
      border-top: 1px solid var(--border-color, #e7e8ea); }
    .board-editor h3 { margin: 0 0 1rem; font-size: 1rem; font-weight: 600; }
    .board-fields { display: flex; flex-wrap: wrap; gap: 1rem; }
    .board-fields mat-form-field { flex: 1 1 230px; }
    .board-error { color: #b3261e; }
    @media(max-width:560px) { .board-entry-info { align-items: flex-start; flex-direction: column; } }
  `]
})
export class BoardPositionsComponent implements OnInit {
  readonly userId = input.required<number>();
  private service = inject(UsersService);
  private snackBar = inject(MatSnackBar);

  readonly roleOptions: {code: BoardRoleCode; label: string}[] = [
    {code: 'presidente', label: 'Presidente'},
    {code: 'secretario', label: 'Secretario'},
    {code: 'tesorero', label: 'Tesorero'},
    {code: 'vicepresidente', label: 'Vicepresidente'},
    {code: 'coordinador_joven', label: 'Coordinador joven'},
    {code: 'otro', label: 'Otro (personalizado)'},
  ];

  positions = signal<BoardPosition[]>([]);
  assignableEntities = signal<BoardPositionEntity[]>([]);
  entityId = signal<number | null>(null);
  role = signal<BoardRoleCode>('presidente');
  customTitle = signal('');
  loading = signal(true);
  saving = signal(false);
  error = signal('');
  canSubmit = computed(() => !!this.entityId() &&
    (this.role() !== 'otro' || this.customTitle().trim().length >= 2));

  ngOnInit(): void {
    forkJoin({
      positions: this.service.getBoardPositions(this.userId()),
      entities: this.service.getBoardPositionEntities(this.userId()),
    }).subscribe({
      next: ({positions, entities}) => {
        this.positions.set(positions);
        this.assignableEntities.set(entities);
        this.entityId.set(entities[0]?.id ?? null);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los cargos de junta.');
        this.loading.set(false);
      },
    });
  }

  canRemove(position: BoardPosition): boolean {
    return this.assignableEntities().some(e => e.id === position.entity_id);
  }

  add(): void {
    const entity_id = this.entityId();
    if (!entity_id || !this.canSubmit() || this.saving()) return;
    this.saving.set(true);
    this.error.set('');
    this.service.addBoardPosition(this.userId(), {
      entity_id,
      role_code: this.role(),
      custom_title: this.role() === 'otro' ? this.customTitle().trim() : null,
    }).subscribe({
      next: position => {
        this.positions.update(items => [...items, position]);
        this.customTitle.set('');
        this.saving.set(false);
        this.snackBar.open('Cargo añadido', 'Cerrar', {duration: 3000});
      },
      error: err => {
        this.saving.set(false);
        this.error.set(err.status === 409
          ? 'La persona ya tiene este cargo en esa entidad.'
          : (err.error?.detail || 'No se pudo añadir el cargo.'));
      },
    });
  }

  remove(position: BoardPosition): void {
    if (!this.canRemove(position) || this.saving()) return;
    this.saving.set(true);
    this.error.set('');
    this.service.deleteBoardPosition(position.id).subscribe({
      next: () => {
        this.positions.update(items => items.filter(item => item.id !== position.id));
        this.saving.set(false);
        this.snackBar.open('Cargo retirado', 'Cerrar', {duration: 3000});
      },
      error: () => {
        this.saving.set(false);
        this.error.set('No se pudo retirar el cargo.');
      }
    });
  }
}
