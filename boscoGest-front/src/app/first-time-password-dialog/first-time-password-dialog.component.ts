import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

export interface FirstTimePasswordChangeRequest {
  new_password: string;
  confirm_password: string;
}

@Component({
  selector: 'app-first-time-password-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatSnackBarModule
  ],
  templateUrl: './first-time-password-dialog.component.html',
  styleUrl: './first-time-password-dialog.component.css'
})
export class FirstTimePasswordDialogComponent {
  changePasswordForm: FormGroup;
  hideNewPassword = true;
  hideConfirmPassword = true;
  isSubmitting = false;

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private snackBar: MatSnackBar,
    private router: Router,
    public dialogRef: MatDialogRef<FirstTimePasswordDialogComponent>
  ) {
    this.changePasswordForm = this.fb.group({
      new_password: ['', [
        Validators.required,
        Validators.minLength(8),
        this.passwordStrengthValidator
      ]],
      confirm_password: ['', [Validators.required]]
    }, {
      validators: this.passwordMatchValidator
    });
  }

  // Validador personalizado para la fortaleza de la contraseña
  private passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    if (!value) {
      return null;
    }

    const hasUpperCase = /[A-Z]/.test(value);
    const hasDigit = /\d/.test(value);

    const passwordValid = hasUpperCase && hasDigit;

    if (!passwordValid) {
      return {
        passwordStrength: {
          hasUpperCase,
          hasDigit
        }
      };
    }

    return null;
  }

  // Validador para verificar que las contraseñas coincidan
  private passwordMatchValidator(group: AbstractControl): ValidationErrors | null {
    const newPassword = group.get('new_password')?.value;
    const confirmPassword = group.get('confirm_password')?.value;

    if (newPassword && confirmPassword && newPassword !== confirmPassword) {
      return { passwordMismatch: true };
    }

    return null;
  }

  onSubmit(): void {
    if (this.changePasswordForm.valid && !this.isSubmitting) {
      this.isSubmitting = true;
      const formValue = this.changePasswordForm.value;

      const request: FirstTimePasswordChangeRequest = {
        new_password: formValue.new_password,
        confirm_password: formValue.confirm_password
      };

      this.http.post(`${environment.apiUrl}/users/first-time-password-change`, request).subscribe({
        next: (response: any) => {
          this.snackBar.open('Contraseña cambiada exitosamente. Por favor, inicia sesión de nuevo.', 'Cerrar', {
            duration: 5000,
            panelClass: ['success-snackbar']
          });
          this.dialogRef.close(true);
          // Redirigir al login para que el usuario inicie sesión con la nueva contraseña
          setTimeout(() => {
            localStorage.removeItem('authToken');
            this.router.navigate(['/login']);
          }, 1000);
        },
        error: (error: HttpErrorResponse) => {
          this.isSubmitting = false;
          let errorMessage = 'Error al cambiar la contraseña';

          if (error.status === 403) {
            errorMessage = 'No tienes permisos para realizar esta acción';
          } else if (error.status === 400) {
            errorMessage = error.error.detail || 'Datos inválidos';
          } else if (error.error?.detail) {
            errorMessage = error.error.detail;
          }

          this.snackBar.open(errorMessage, 'Cerrar', {
            duration: 5000,
            panelClass: ['error-snackbar']
          });
        }
      });
    }
  }

  // Helper para obtener mensajes de error
  getPasswordErrorMessage(): string {
    const control = this.changePasswordForm.get('new_password');
    if (control?.hasError('required')) {
      return 'La contraseña es requerida';
    }
    if (control?.hasError('minlength')) {
      return 'La contraseña debe tener al menos 8 caracteres';
    }
    if (control?.hasError('passwordStrength')) {
      const errors = control.getError('passwordStrength');
      if (!errors.hasUpperCase) {
        return 'La contraseña debe contener al menos una letra mayúscula';
      }
      if (!errors.hasDigit) {
        return 'La contraseña debe contener al menos un número';
      }
    }
    return '';
  }

  getConfirmPasswordErrorMessage(): string {
    if (this.changePasswordForm.hasError('passwordMismatch')) {
      return 'Las contraseñas no coinciden';
    }
    const control = this.changePasswordForm.get('confirm_password');
    if (control?.hasError('required')) {
      return 'Debe confirmar la contraseña';
    }
    return '';
  }
}
