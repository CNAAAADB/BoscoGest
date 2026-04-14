import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ResourcesService } from '../resources.service';

export interface CategoryDialogData {
  entityId: number;
}

@Component({
  selector: 'app-category-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
  ],
  template: `
    <h2 mat-dialog-title>Nueva Categoría</h2>
    <mat-dialog-content>
      <form [formGroup]="form" class="category-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Nombre</mat-label>
          <input matInput formControlName="name" placeholder="Nombre de la categoría" required>
          @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
            <mat-error>El nombre es requerido</mat-error>
          }
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Descripción (opcional)</mat-label>
          <textarea matInput formControlName="description" placeholder="Descripción de la categoría" rows="3"></textarea>
        </mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="onCancel()">Cancelar</button>
      <button mat-raised-button color="primary" (click)="onSubmit()" [disabled]="!form.valid || submitting">
        {{ submitting ? 'Creando...' : 'Crear' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    .category-form {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      min-width: 300px;
    }
    .full-width {
      width: 100%;
    }
  `]
})
export class CategoryDialogComponent {
  form: FormGroup;
  submitting = false;

  constructor(
    private fb: FormBuilder,
    private resourcesService: ResourcesService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<CategoryDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: CategoryDialogData,
  ) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      description: ['', [Validators.maxLength(500)]],
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onSubmit(): void {
    if (!this.form.valid) return;

    this.submitting = true;
    this.resourcesService.createCategory({
      name: this.form.value.name,
      description: this.form.value.description || null,
      entity_id: this.data.entityId,
    }).subscribe({
      next: (category) => {
        this.snackBar.open('Categoría creada correctamente', 'Cerrar', { duration: 3000 });
        this.dialogRef.close(category);
      },
      error: () => {
        this.snackBar.open('Error al crear la categoría', 'Cerrar', { duration: 3000 });
        this.submitting = false;
      }
    });
  }
}
