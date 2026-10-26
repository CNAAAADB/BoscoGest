import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FeeAssignmentResponse } from '../../models/user.model';
import { FeesService } from '../fees.service';

/**
 * Sending the receipt for a fee.
 *
 * There is no payment gateway: the member transfers the money at their bank and
 * this is how the association finds out. That makes it the payment step, not an
 * attachment — so it says what to transfer and where the money is going before
 * asking for the file.
 */
@Component({
  selector: 'app-submit-proof-dialog',
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './submit-proof-dialog.component.html',
  styleUrl: './submit-proof-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubmitProofDialogComponent {
  private dialogRef = inject(MatDialogRef<SubmitProofDialogComponent>);
  private feesService = inject(FeesService);
  readonly assignment: FeeAssignmentResponse = inject(MAT_DIALOG_DATA).assignment;

  file = signal<File | null>(null);
  reference = signal('');
  submitting = signal(false);
  errorMessage = signal<string | null>(null);

  /** Mirrors the server's limit, so a large file fails here and not after the upload. */
  private readonly MAX_BYTES = 10 * 1024 * 1024;
  private readonly ACCEPTED = ['application/pdf', 'image/jpeg', 'image/png', 'image/heic'];

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const chosen = input.files?.[0] ?? null;
    this.errorMessage.set(null);

    if (!chosen) {
      this.file.set(null);
      return;
    }
    if (!this.ACCEPTED.includes(chosen.type)) {
      this.errorMessage.set('El justificante debe ser un PDF o una imagen (JPG, PNG o HEIC).');
      this.file.set(null);
      return;
    }
    if (chosen.size > this.MAX_BYTES) {
      this.errorMessage.set('El archivo supera los 10 MB. Prueba a enviarlo como PDF.');
      this.file.set(null);
      return;
    }
    this.file.set(chosen);
  }

  clearFile(): void {
    this.file.set(null);
  }

  onSubmit(): void {
    const chosen = this.file();
    if (!chosen || this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set(null);

    this.feesService
      .submitProof(this.assignment.id, chosen, this.reference().trim() || undefined)
      .subscribe({
        next: (updated) => {
          this.submitting.set(false);
          this.dialogRef.close(updated);
        },
        error: (error) => {
          this.submitting.set(false);
          this.errorMessage.set(
            error?.error?.detail ??
              'No se ha podido enviar el justificante. Inténtalo de nuevo.'
          );
        },
      });
  }
}
