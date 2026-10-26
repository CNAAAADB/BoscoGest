import { Component, Inject, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FeesService } from '../fees.service';
import { FeeConfigResponse, FeeResponse } from '../../models/user.model';
import { NativePickerDirective } from '../../shared/native-picker.directive';

export interface FeeHistoryDialogData {
  fee: FeeResponse;
  canManage: boolean;
}

@Component({
  selector: 'app-fee-history-dialog',
  standalone: true,
  imports: [
    NativePickerDirective,
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
  ],
  templateUrl: './fee-history-dialog.component.html',
  styleUrl: './fee-history-dialog.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FeeHistoryDialogComponent implements OnInit {
  history = signal<FeeConfigResponse[]>([]);
  loading = signal(true);
  saving = signal(false);
  changed = false;

  versionForm!: FormGroup;
  readonly columns = ['amount', 'valid_from', 'valid_until', 'created_at'];

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: FeeHistoryDialogData,
    private dialogRef: MatDialogRef<FeeHistoryDialogComponent>,
    private feesService: FeesService,
    private fb: FormBuilder,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.versionForm = this.fb.group({
      amount: [null, [Validators.required, Validators.min(0.01)]],
      valid_from: ['', Validators.required],
      valid_until: [null],
    });
    this.loadHistory();
  }

  loadHistory(): void {
    this.loading.set(true);
    this.feesService.getFeeHistory(this.data.fee.id).subscribe({
      next: (h) => { this.history.set(h); this.loading.set(false); },
      error: () => {
        this.snackBar.open('Error al cargar el histórico', 'Cerrar', { duration: 3000 });
        this.loading.set(false);
      },
    });
  }

  addVersion(): void {
    if (this.versionForm.invalid) return;
    this.saving.set(true);
    const { amount, valid_from, valid_until } = this.versionForm.value;
    this.feesService.addFeeVersion(this.data.fee.id, {
      amount,
      valid_from,
      valid_until: valid_until || null,
    }).subscribe({
      next: () => {
        this.snackBar.open('Nueva versión añadida', 'Cerrar', { duration: 2500 });
        this.versionForm.reset();
        this.saving.set(false);
        this.changed = true;
        this.loadHistory();
      },
      error: () => {
        this.snackBar.open('Error al añadir la versión', 'Cerrar', { duration: 3000 });
        this.saving.set(false);
      },
    });
  }

  close(): void {
    this.dialogRef.close(this.changed);
  }
}
