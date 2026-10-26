import { Component, Inject, ChangeDetectionStrategy} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  /**
   * 'info' drops the confirm button and leaves only a way out. For telling
   * someone why an action is not available, rather than asking them to
   * approve one.
   */
  variant?: 'confirm' | 'info';
  /** Extra lines under the message — a list of what is affected. */
  details?: string[];
  /** Highlights the confirm button as destructive. */
  danger?: boolean;
}

@Component({
  selector: 'app-confirm-dialog',
  imports: [MatDialogModule, MatButtonModule],
  templateUrl: './confirm-dialog.component.html',
  styleUrl: './confirm-dialog.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConfirmDialogComponent {
  constructor(
    public dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData
  ) {
    // Set defaults
    this.data.variant = this.data.variant || 'confirm';
    this.data.confirmText = this.data.confirmText || 'Confirmar';
    this.data.cancelText =
      this.data.cancelText || (this.data.variant === 'info' ? 'Entendido' : 'Cancelar');
  }

  onConfirm(): void {
    this.dialogRef.close(true);
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }
}
