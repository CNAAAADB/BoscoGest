import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { UsersService } from '../users/users.service';

/**
 * Borrado de la propia cuenta.
 *
 * Google Play exige esta vía dentro de la app para cualquier aplicación con
 * registro público, y el RGPD la exige igualmente. Pide contraseña y una
 * confirmación explícita porque no hay vuelta atrás.
 */
@Component({
  selector: 'app-delete-account-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSnackBarModule
  ],
  templateUrl: './delete-account-dialog.component.html',
  styleUrl: './delete-account-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DeleteAccountDialogComponent {
  private fb = inject(FormBuilder);
  private usersService = inject(UsersService);
  private snackBar = inject(MatSnackBar);
  dialogRef = inject(MatDialogRef<DeleteAccountDialogComponent>);

  hidePassword = true;
  // Signals: se cambian dentro de callbacks asíncronos y con OnPush una
  // asignación normal no refrescaría los botones enlazados.
  isSubmitting = signal(false);
  errorMessage = signal<string | null>(null);

  deleteForm: FormGroup = this.fb.group({
    password: ['', [Validators.required]],
    understood: [false, [Validators.requiredTrue]]
  });

  onSubmit(): void {
    if (this.deleteForm.invalid || this.isSubmitting()) {
      return;
    }

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    this.usersService.deleteMyAccount(this.deleteForm.value.password).subscribe({
      next: () => {
        // El diálogo se cierra con true y quien lo abrió cierra la sesión: el
        // token ya está revocado en el servidor.
        this.dialogRef.close(true);
      },
      error: (error: HttpErrorResponse) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(this.messageFor(error));
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }

  private messageFor(error: HttpErrorResponse): string {
    if (error.status === 401) {
      return 'La contraseña no es correcta.';
    }
    // 409: es la única cuenta con administración total. El backend explica por
    // qué, y ese texto es más útil que cualquiera genérico de aquí.
    if (error.status === 409 && error.error?.detail) {
      return error.error.detail;
    }
    if (error.error?.detail && typeof error.error.detail === 'string') {
      return error.error.detail;
    }
    return 'No se ha podido eliminar la cuenta. Inténtalo de nuevo más tarde.';
  }
}
