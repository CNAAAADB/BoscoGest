import { Component, inject, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

export interface RejectReasonData {
  userName: string;
}

@Component({
  selector: 'app-reject-reason-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  template: `
    <h2 mat-dialog-title>Rechazar solicitud</h2>
    <mat-dialog-content>
      <p>¿Rechazar la solicitud de <strong>{{ data.userName }}</strong>?</p>
      <mat-form-field appearance="outline" style="width:100%">
        <mat-label>Motivo (opcional)</mat-label>
        <textarea
          matInput
          rows="3"
          [value]="reason()"
          (input)="reason.set($any($event.target).value)"
          placeholder="Puedes indicar el motivo del rechazo..."
        ></textarea>
      </mat-form-field>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="cancel()">Cancelar</button>
      <button mat-raised-button color="warn" (click)="confirm()">Rechazar</button>
    </mat-dialog-actions>
  `,

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RejectReasonDialogComponent {
  data = inject<RejectReasonData>(MAT_DIALOG_DATA);
  private dialogRef = inject(MatDialogRef<RejectReasonDialogComponent>);
  reason = signal('');

  confirm(): void {
    this.dialogRef.close(this.reason());
  }

  cancel(): void {
    // Close with undefined to signal "cancelled"
    this.dialogRef.close(undefined);
  }
}
