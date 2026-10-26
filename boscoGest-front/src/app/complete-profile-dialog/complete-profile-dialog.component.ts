import { Component, Inject, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { UsersService } from '../users/users.service';
import { UserResponse, UserUpdate, UserSize, USER_SIZE_OPTIONS } from '../models/user.model';

interface ProfileField {
  key: keyof UserUpdate;
  label: string;
  type: 'text' | 'email' | 'tel' | 'date' | 'select' | 'iban';
  icon: string;
}

@Component({
  selector: 'app-complete-profile-dialog',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatIconModule,
    MatSnackBarModule,
  ],
  templateUrl: './complete-profile-dialog.component.html',
  styleUrl: './complete-profile-dialog.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CompleteProfileDialogComponent {
  form: FormGroup;
  readonly sizeOptions = USER_SIZE_OPTIONS;
  fields: ProfileField[] = [];
  // Signal rather than a plain field: it is flipped inside async
  // callbacks, and under OnPush a plain assignment would not refresh
  // the buttons bound to it.
  isSubmitting = signal(false);

  // All profile fields that the user can fill in. Only the empty ones are shown.
  private readonly candidateFields: ProfileField[] = [
    { key: 'email', label: 'Email', type: 'email', icon: 'email' },
    { key: 'phone', label: 'Teléfono', type: 'tel', icon: 'phone' },
    { key: 'address', label: 'Dirección', type: 'text', icon: 'home' },
    { key: 'iban', label: 'IBAN', type: 'iban', icon: 'account_balance' },
    { key: 'size', label: 'Talla', type: 'select', icon: 'straighten' },
    { key: 'hobbies', label: 'Hobbies', type: 'text', icon: 'interests' },
    { key: 'job_position', label: 'Puesto de trabajo', type: 'text', icon: 'work' },
  ];

  constructor(
    private fb: FormBuilder,
    private usersService: UsersService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<CompleteProfileDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public user: UserResponse,
  ) {
    this.fields = this.candidateFields.filter(
      (f) => !this.user || !this.user[f.key as keyof UserResponse],
    );

    const group: Record<string, any> = {};
    for (const field of this.fields) {
      group[field.key] = field.type === 'email' ? ['', Validators.email] : [''];
    }
    this.form = this.fb.group(group);
  }

  get hasFields(): boolean {
    return this.fields.length > 0;
  }

  onSave(): void {
    if (this.form.invalid || this.isSubmitting()) {
      return;
    }

    const patch: UserUpdate = {};
    for (const field of this.fields) {
      const value = this.form.get(field.key)?.value;
      if (value !== null && value !== undefined && value !== '') {
        (patch as any)[field.key] = value;
      }
    }

    if (Object.keys(patch).length === 0) {
      this.dialogRef.close(false);
      return;
    }

    this.isSubmitting.set(true);
    this.usersService.updateMyProfile(patch).subscribe({
      next: () => {
        this.snackBar.open('Perfil actualizado correctamente.', 'Cerrar', {
          duration: 3000,
          panelClass: ['success-snackbar'],
        });
        this.dialogRef.close(true);
      },
      error: (error) => {
        this.isSubmitting.set(false);
        const detail = error?.error?.detail || 'No se pudo actualizar el perfil';
        this.snackBar.open(detail, 'Cerrar', {
          duration: 4000,
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  onSkip(): void {
    this.dialogRef.close(false);
  }
}
