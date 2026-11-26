import { Component, OnInit, signal, computed, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FeesService } from '../fees.service';
import { AuthService } from '../../auth/auth.service';
import { ConfirmDialogComponent, ConfirmDialogData } from '../../confirm-dialog/confirm-dialog.component';
import {
  FeeHistoryDialogComponent,
  FeeHistoryDialogData,
} from '../fee-history-dialog/fee-history-dialog.component';
import {
  EntityResponse,
  FeeResponse,
  FeeAssignmentResponse,
  FeeStatus,
  FeePeriodicity,
  FEE_STATUS_LABELS,
  FEE_STATUS_COLORS,
  FEE_PERIODICITY_LABELS,
  FEE_PERIODICITY_OPTIONS,
  MemberPreview,
  FeeSubscriptionResponse
} from '../../models/user.model';
import { NativePickerDirective } from '../../shared/native-picker.directive';

@Component({
  selector: 'app-fee-admin',
  standalone: true,
  imports: [
    NativePickerDirective,
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatTabsModule,
    MatTableModule,
    MatCheckboxModule,
    MatTooltipModule,
  ],
  templateUrl: './fee-admin.component.html',
  styleUrl: './fee-admin.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FeeAdminComponent implements OnInit {
  // Shared entity selector
  entities = signal<EntityResponse[]>([]);
  selectedEntityId = signal<number | null>(null);

  // Fees tab
  fees = signal<FeeResponse[]>([]);
  loadingFees = signal(false);
  creatingFee = signal(false);
  newFeeForm!: FormGroup;

  // Assignments tab
  assignFeeId = signal<number | null>(null);
  members = signal<MemberPreview[]>([]);
  selectedUserIds = signal<Set<number>>(new Set());
  loadingMembers = signal(false);
  generating = signal(false);
  assignForm!: FormGroup;

  assignments = signal<FeeAssignmentResponse[]>([]);
  loadingAssignments = signal(false);
  filterPeriod = signal('');
  filterStatus = signal<FeeStatus | ''>('');

  readonly statusLabels = FEE_STATUS_LABELS;
  readonly statusColors = FEE_STATUS_COLORS;
  readonly periodicityLabels = FEE_PERIODICITY_LABELS;
  readonly periodicityOptions = FEE_PERIODICITY_OPTIONS;
  readonly feeColumns = ['name', 'periodicity', 'renew', 'amount', 'valid_from', 'valid_until', 'actions'];
  readonly memberColumns = ['select', 'member', 'role', 'state'];
  readonly assignmentColumns = ['user', 'fee', 'periodicity', 'period', 'amount', 'due_date', 'status', 'actions'];
  readonly allStatuses: FeeStatus[] = ['pending', 'paid', 'overdue', 'cancelled'];

  selectedFee = computed(() => this.fees().find(f => f.id === this.assignFeeId()) ?? null);

  selectableMembers = computed(() => this.members().filter(m => !m.already_assigned));

  allSelectableChecked = computed(() => {
    const selectable = this.selectableMembers();
    const sel = this.selectedUserIds();
    return selectable.length > 0 && selectable.every(m => sel.has(m.user_id));
  });

  someSelectableChecked = computed(() => {
    const sel = this.selectedUserIds();
    return this.selectableMembers().some(m => sel.has(m.user_id)) && !this.allSelectableChecked();
  });

  filteredAssignments = computed(() => {
    let list = this.assignments();
    const period = this.filterPeriod();
    const status = this.filterStatus();
    if (period) list = list.filter(a => a.period === period);
    if (status) list = list.filter(a => a.status === status);
    return list;
  });

  periods = computed(() => {
    const all = this.assignments().map(a => a.period);
    return [...new Set(all)].sort().reverse();
  });

  canManage = computed(() => this.entities().find(e => e.id === this.selectedEntityId())?.permissions?.fee_manage === true);
  canCreate = computed(() => this.entities().find(e => e.id === this.selectedEntityId())?.permissions?.fee_create === true);

  constructor(
    private feesService: FeesService,
    private authService: AuthService,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
    private fb: FormBuilder,
  ) {}

  ngOnInit(): void {
    this.newFeeForm = this.fb.group({
      name: ['', Validators.required],
      periodicity: ['annual', Validators.required],
      // 9 = September, matching the course. Calendar years remain available
      // for fees that genuinely run January to December.
      period_start_month: [9, Validators.required],
      amount: [null, [Validators.required, Validators.min(0.01)]],
      valid_from: ['', Validators.required],
      valid_until: [null],
      entity_ids: [[], Validators.required],
      auto_renew: [false],
      reminder_days: [7, [Validators.required, Validators.min(0)]],
    });

    // Period is derived from the fee's periodicity + this reference date (optional, default today)
    this.assignForm = this.fb.group({
      reference_date: [null],
      due_date: [null],
    });

    this.feesService.getFeeEntities().subscribe({
      next: (entities) => {
        this.entities.set(entities);
        if (entities.length > 0) {
          this.selectEntity(entities[0].id);
        }
      },
      error: () => this.snackBar.open('Error al cargar las entidades', 'Cerrar', { duration: 3000 }),
    });
  }

  selectEntity(entityId: number): void {
    this.selectedEntityId.set(entityId);
    this.newFeeForm.patchValue({ entity_ids: [entityId] });
    this.assignFeeId.set(null);
    this.members.set([]);
    this.selectedUserIds.set(new Set());
    this.loadFees();
    this.loadAssignments();
  }

  // ── Fees tab ────────────────────────────────────────────────────────────

  loadFees(): void {
    const entityId = this.selectedEntityId();
    if (!entityId) return;
    this.loadingFees.set(true);
    this.feesService.listFees(entityId).subscribe({
      next: (fees) => { this.fees.set(fees); this.loadingFees.set(false); },
      error: () => {
        this.snackBar.open('Error al cargar las cuotas', 'Cerrar', { duration: 3000 });
        this.loadingFees.set(false);
      },
    });
  }

  createFee(): void {
    if (this.newFeeForm.invalid) return;
    this.creatingFee.set(true);
    const { name, periodicity, amount, valid_from, valid_until, entity_ids,
            auto_renew, reminder_days, period_start_month } = this.newFeeForm.value;
    this.feesService.createFee({
      name,
      periodicity,
      amount,
      valid_from,
      valid_until: valid_until || null,
      entity_ids,
      auto_renew,
      reminder_days,
      // Weekly and monthly fees do not follow a yearly cycle, so the field is
      // hidden for them and the calendar default applies.
      period_start_month:
        periodicity === 'weekly' || periodicity === 'monthly' ? 1 : period_start_month,
    }).subscribe({
      next: (created) => {
        this.snackBar.open(`Cuota creada en ${created.length} entidad(es)`, 'Cerrar', { duration: 3000 });
        this.creatingFee.set(false);
        this.newFeeForm.reset({
          entity_ids: [this.selectedEntityId()],
          periodicity: 'annual', auto_renew: false, reminder_days: 7,
        });
        this.loadFees();
      },
      error: (err) => {
        const msg = err?.status === 403
          ? 'No tienes permiso en alguna de las entidades seleccionadas'
          : 'Error al crear la cuota';
        this.snackBar.open(msg, 'Cerrar', { duration: 4000 });
        this.creatingFee.set(false);
      },
    });
  }

  openHistory(fee: FeeResponse): void {
    this.dialog.open(FeeHistoryDialogComponent, {
      data: { fee, canManage: this.canCreate() } as FeeHistoryDialogData,
      width: '640px',
    }).afterClosed().subscribe((changed) => {
      if (changed) this.loadFees();
    });
  }

  deleteFee(fee: FeeResponse): void {
    this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Eliminar cuota',
        message: `¿Eliminar la cuota "${fee.name}"? Se desactivará junto con su histórico.`,
        confirmText: 'Eliminar',
        cancelText: 'Cancelar',
      } as ConfirmDialogData
    }).afterClosed().subscribe(confirmed => {
      if (!confirmed) return;
      this.feesService.deleteFee(fee.id).subscribe({
        next: () => {
          this.snackBar.open('Cuota eliminada', 'Cerrar', { duration: 2500 });
          this.loadFees();
        },
        error: () => this.snackBar.open(
          'No se puede eliminar: tiene asignaciones activas', 'Cerrar', { duration: 4000 }),
      });
    });
  }

  // ── Assignments tab ───────────────────────────────────────────────────────

  onAssignFeeChange(feeId: number): void {
    this.assignFeeId.set(feeId);
    this.members.set([]);
    this.selectedUserIds.set(new Set());
  }

  loadMembersPreview(): void {
    const feeId = this.assignFeeId();
    if (!feeId) {
      this.snackBar.open('Selecciona una cuota primero', 'Cerrar', { duration: 2500 });
      return;
    }
    const refDate = this.assignForm.get('reference_date')?.value || undefined;
    this.loadingMembers.set(true);
    this.feesService.getMembersPreview(feeId, refDate).subscribe({
      next: (members) => {
        this.members.set(members);
        // Preselect all not-yet-assigned members
        this.selectedUserIds.set(new Set(members.filter(m => !m.already_assigned).map(m => m.user_id)));
        this.loadingMembers.set(false);
      },
      error: () => {
        this.snackBar.open('Error al cargar los socios', 'Cerrar', { duration: 3000 });
        this.loadingMembers.set(false);
      },
    });
  }

  toggleMember(userId: number): void {
    const sel = new Set(this.selectedUserIds());
    if (sel.has(userId)) sel.delete(userId); else sel.add(userId);
    this.selectedUserIds.set(sel);
  }

  toggleAll(): void {
    if (this.allSelectableChecked()) {
      this.selectedUserIds.set(new Set());
    } else {
      this.selectedUserIds.set(new Set(this.selectableMembers().map(m => m.user_id)));
    }
  }

  isSelected(userId: number): boolean {
    return this.selectedUserIds().has(userId);
  }

  // ── Roster ────────────────────────────────────────────────────────────────
  //
  // Enrolling is done once; generating then charges whoever is enrolled. It
  // used to be the other way round — pick the members every period — which is
  // what let the set of payers drift from one period to the next.

  subscriptions = signal<FeeSubscriptionResponse[]>([]);
  loadingSubscriptions = signal(false);

  loadSubscriptions(): void {
    const feeId = this.assignFeeId();
    if (!feeId) return;
    this.loadingSubscriptions.set(true);
    this.feesService.listSubscriptions(feeId).subscribe({
      next: (list) => {
        this.subscriptions.set(list);
        this.loadingSubscriptions.set(false);
      },
      error: () => {
        this.snackBar.open('Error al cargar el padrón de la cuota', 'Cerrar', { duration: 3000 });
        this.loadingSubscriptions.set(false);
      },
    });
  }

  subscribeSelected(exempt = false): void {
    const feeId = this.assignFeeId();
    const userIds = [...this.selectedUserIds()];
    if (!feeId || userIds.length === 0) {
      this.snackBar.open('Selecciona al menos un socio', 'Cerrar', { duration: 2500 });
      return;
    }
    this.feesService.subscribe(feeId, { user_ids: userIds, exempt }).subscribe({
      next: (rows) => {
        this.snackBar.open(
          exempt
            ? `${rows.length} socio(s) dados de alta como exentos`
            : `${rows.length} socio(s) dados de alta en la cuota`,
          'Cerrar', { duration: 4000, panelClass: 'success-snackbar' });
        this.selectedUserIds.set(new Set());
        this.loadSubscriptions();
        this.loadMembersPreview();
      },
      error: () =>
        this.snackBar.open('Error al dar de alta', 'Cerrar', { duration: 3000 }),
    });
  }

  unsubscribe(sub: FeeSubscriptionResponse): void {
    const feeId = this.assignFeeId();
    if (!feeId) return;
    this.feesService.unsubscribe(feeId, sub.user_id).subscribe({
      next: () => {
        this.snackBar.open(
          'Alta finalizada. Las cuotas ya emitidas se conservan.',
          'Cerrar', { duration: 4000 });
        this.loadSubscriptions();
      },
      error: () => this.snackBar.open('Error al dar de baja', 'Cerrar', { duration: 3000 }),
    });
  }

  toggleExempt(sub: FeeSubscriptionResponse): void {
    const feeId = this.assignFeeId();
    if (!feeId) return;
    const next = !sub.exempt;
    const reason = next
      ? (window.prompt('Motivo de la exención (p. ej. socio de honor):') ?? '').trim()
      : null;
    // An exemption with no reason is indistinguishable from a mistake later on.
    if (next && !reason) {
      return;
    }
    this.feesService.setExemption(feeId, sub.user_id, next, reason).subscribe({
      next: () => {
        this.snackBar.open(
          next ? 'Socio marcado como exento' : 'Exención retirada',
          'Cerrar', { duration: 3000 });
        this.loadSubscriptions();
      },
      error: () => this.snackBar.open('Error al cambiar la exención', 'Cerrar', { duration: 3000 }),
    });
  }

  generate(): void {
    const feeId = this.assignFeeId();
    if (!feeId) return;
    if (this.subscriptions().length === 0) {
      this.snackBar.open(
        'Da de alta primero a los socios que pagan esta cuota',
        'Cerrar', { duration: 4000 });
      return;
    }
    this.generating.set(true);
    const { reference_date, due_date } = this.assignForm.value;
    // No user_ids: the roster decides who is charged.
    this.feesService.generateAssignments({
      fee_id: feeId,
      reference_date: reference_date || null,
      due_date: due_date || null,
    }).subscribe({
      next: (result) => {
        const parts = [`${result.created} nuevas`];
        if (result.exempt) parts.push(`${result.exempt} exentas`);
        if (result.skipped) parts.push(`${result.skipped} ya existían`);
        this.snackBar.open(`Generadas: ${parts.join(', ')}`, 'Cerrar', { duration: 5000 });
        this.generating.set(false);
        this.loadMembersPreview();
        this.loadAssignments();
      },
      error: () => {
        this.snackBar.open('Error al generar las asignaciones', 'Cerrar', { duration: 3000 });
        this.generating.set(false);
      },
    });
  }

  // ── Proof review ──────────────────────────────────────────────────────────

  acceptProof(assignment: FeeAssignmentResponse): void {
    this.changeStatus(assignment, 'paid');
  }

  rejectProof(assignment: FeeAssignmentResponse): void {
    const reason = window.prompt(
      'Motivo por el que devuelves el justificante (lo verá el socio):'
    );
    if (!reason || !reason.trim()) {
      return;
    }
    this.feesService.rejectProof(assignment.id, reason.trim()).subscribe({
      next: (updated) => {
        this.assignments.update(list => list.map(a => a.id === updated.id ? updated : a));
        this.snackBar.open('Justificante devuelto al socio', 'Cerrar', { duration: 4000 });
      },
      error: () =>
        this.snackBar.open('Error al devolver el justificante', 'Cerrar', { duration: 3000 }),
    });
  }

  viewProof(assignment: FeeAssignmentResponse): void {
    this.feesService.getProofUrl(assignment.id).subscribe({
      next: ({ url }) => window.open(url, '_blank', 'noopener'),
      error: () =>
        this.snackBar.open('No se ha podido abrir el justificante', 'Cerrar', { duration: 3000 }),
    });
  }

  /** Charges whose receipt is waiting to be checked — the treasurer's queue. */
  pendingProofs = computed(() =>
    this.assignments().filter(a => a.status === 'submitted')
  );

  loadAssignments(): void {
    this.assignments.set([]);
    if (!this.canManage()) return;
    const entityId = this.selectedEntityId();
    if (!entityId) return;
    this.loadingAssignments.set(true);
    this.feesService.listAssignments(entityId).subscribe({
      next: (list) => { this.assignments.set(list); this.loadingAssignments.set(false); },
      error: () => {
        this.snackBar.open('Error al cargar las asignaciones', 'Cerrar', { duration: 3000 });
        this.loadingAssignments.set(false);
      },
    });
  }

  changeStatus(assignment: FeeAssignmentResponse, status: FeeStatus): void {
    this.feesService.updateAssignmentStatus(assignment.id, { status }).subscribe({
      next: (updated) => {
        this.assignments.update(list => list.map(a => a.id === updated.id ? updated : a));
        this.snackBar.open('Estado actualizado', 'Cerrar', { duration: 2000 });
      },
      error: () => this.snackBar.open('Error al actualizar el estado', 'Cerrar', { duration: 3000 }),
    });
  }

  onFilterPeriod(value: string): void { this.filterPeriod.set(value); }
  onFilterStatus(value: FeeStatus | ''): void { this.filterStatus.set(value); }
  clearFilters(): void { this.filterPeriod.set(''); this.filterStatus.set(''); }

  getStatusLabel(status: FeeStatus): string { return FEE_STATUS_LABELS[status] ?? status; }
  getStatusColor(status: FeeStatus): string { return FEE_STATUS_COLORS[status] ?? '#9e9e9e'; }
  getPeriodicityLabel(p: FeePeriodicity): string { return FEE_PERIODICITY_LABELS[p] ?? p; }

  /**
   * What the treasurer can set a charge to from here.
   *
   * Two states are deliberately absent from every list. `submitted` is reached
   * by the member attaching a receipt, not by an admin declaring it. `exempt`
   * belongs to the enrolment — a member is exempt from the fee, not from one
   * period of it — so it is set on the roster, not on a charge.
   */
  /** Months a yearly cycle can start on, named rather than numbered. */
  readonly cycleStartMonths = [
    { value: 1, label: 'Enero (año natural)' },
    { value: 7, label: 'Julio' },
    { value: 9, label: 'Septiembre (curso)' },
    { value: 10, label: 'Octubre' },
  ];

  nextStatuses(current: FeeStatus): FeeStatus[] {
    const transitions: Record<FeeStatus, FeeStatus[]> = {
      pending: ['paid', 'overdue', 'cancelled'],
      // A receipt is waiting: accept it, or send it back with a reason, which
      // is a separate action because the reason is required.
      submitted: ['paid'],
      overdue: ['paid', 'cancelled'],
      paid: [],
      cancelled: ['pending'],
      exempt: [],
    };
    return transitions[current] ?? [];
  }
}
