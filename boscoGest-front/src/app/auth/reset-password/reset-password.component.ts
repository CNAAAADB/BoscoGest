import { Component, OnInit, signal, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '../auth.service';
import { PostLoginFlowService } from '../post-login-flow.service';

type FailureReason = 'expired' | 'used' | 'invalid';

/** Same rules the backend applies: 8 characters, an uppercase letter, a digit. */
function strength(control: AbstractControl): ValidationErrors | null {
  const value: string = control.value || '';
  if (!value) {
    return null;
  }
  const hasUpperCase = /[A-Z]/.test(value);
  const hasDigit = /\d/.test(value);
  return hasUpperCase && hasDigit ? null : { passwordStrength: { hasUpperCase, hasDigit } };
}

function matching(group: AbstractControl): ValidationErrors | null {
  const a = group.get('new_password')?.value;
  const b = group.get('confirm_password')?.value;
  return a && b && a !== b ? { passwordMismatch: true } : null;
}

/**
 * Where the link in a forgotten-password email lands.
 *
 * Unlike the activation link, arriving spends nothing: the link goes to the
 * server together with the new password, so a mistyped password or a dropped
 * connection leaves it usable for another try.
 */
@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  templateUrl: './reset-password.component.html',
  styleUrl: '../activate/activate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResetPasswordComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private postLoginFlow = inject(PostLoginFlowService);

  private token = '';

  form = this.fb.nonNullable.group(
    {
      new_password: ['', [Validators.required, Validators.minLength(8), strength]],
      confirm_password: ['', [Validators.required]],
    },
    { validators: matching }
  );

  hidePassword = signal(true);
  saving = signal(false);
  failure = signal<FailureReason | null>(null);
  failureMessage = signal('');
  /** A problem worth retrying (the connection), shown above the button. */
  error = signal('');

  ngOnInit(): void {
    this.token = this.route.snapshot.queryParamMap.get('token') ?? '';
    if (!this.token) {
      this.failure.set('invalid');
      this.failureMessage.set('Falta el enlace. Ábrelo desde el correo que recibiste.');
    }
  }

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }

    const { new_password, confirm_password } = this.form.getRawValue();
    this.saving.set(true);
    this.error.set('');
    this.authService.resetPassword(this.token, new_password, confirm_password).subscribe({
      next: () => {
        this.saving.set(false);
        // Signed in with the new password; on to the usual steps after a login.
        this.postLoginFlow.run(() => this.router.navigate(['/login']));
      },
      error: (err) => {
        this.saving.set(false);
        const detail = err?.error?.detail;
        if (detail?.reason) {
          this.failure.set(detail.reason as FailureReason);
          this.failureMessage.set(detail.message);
        } else {
          this.error.set('No hemos podido guardar la contraseña. Comprueba la conexión e inténtalo de nuevo.');
        }
      },
    });
  }

  passwordError(): string {
    const control = this.form.controls.new_password;
    if (control.hasError('required')) {
      return 'Escribe la contraseña nueva';
    }
    if (control.hasError('minlength')) {
      return 'Debe tener al menos 8 caracteres';
    }
    const strengthError = control.getError('passwordStrength');
    if (strengthError && !strengthError.hasUpperCase) {
      return 'Debe tener al menos una letra mayúscula';
    }
    if (strengthError && !strengthError.hasDigit) {
      return 'Debe tener al menos un número';
    }
    return '';
  }
}
