import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MagazinesService } from '../magazines.service';
import { MagazineDetails } from '../../models/user.model';

@Component({
  selector: 'app-magazine-edit',
  standalone: true,
  imports: [
    CommonModule,
    DatePipe,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './magazine-edit.component.html',
  styleUrl: './magazine-edit.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MagazineEditComponent implements OnInit {
  editForm: FormGroup;
  magazine = signal<MagazineDetails | null>(null);
  loading = signal<boolean>(true);
  saving = signal<boolean>(false);
  magazineId: number | null = null;

  constructor(
    private fb: FormBuilder,
    private magazinesService: MagazinesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.editForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      collection: ['', [Validators.maxLength(100)]],
      issue_number: ['', [Validators.min(1)]],
      description: ['', [Validators.maxLength(1000)]]
    });
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.magazineId = parseInt(id, 10);
      this.loadMagazine(this.magazineId);
    } else {
      this.snackBar.open('ID de revista no válido', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      this.router.navigate(['/magazines']);
    }
  }

  loadMagazine(id: number): void {
    this.loading.set(true);
    this.magazinesService.getMagazineDetails(id).subscribe({
      next: (magazine) => {
        this.magazine.set(magazine);
        this.editForm.patchValue({
          title: magazine.title,
          collection: magazine.collection || '',
          issue_number: magazine.issue_number || '',
          description: magazine.description || ''
        });
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading magazine:', error);
        this.snackBar.open('Error al cargar la revista', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/magazines']);
      }
    });
  }

  onSubmit(): void {
    if (this.editForm.valid && this.magazineId) {
      this.saving.set(true);

      const magazineUpdate = {
        title: this.editForm.value.title,
        collection: this.editForm.value.collection || null,
        issue_number: this.editForm.value.issue_number || null,
        description: this.editForm.value.description || null
      };

      this.magazinesService.updateMagazine(this.magazineId, magazineUpdate).subscribe({
        next: (magazine) => {
          this.snackBar.open('Revista actualizada correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.saving.set(false);
          this.router.navigate(['/magazines', magazine.id]);
        },
        error: (error) => {
          console.error('Error updating magazine:', error);
          this.snackBar.open('Error al actualizar la revista', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.saving.set(false);
        }
      });
    } else {
      this.snackBar.open('Por favor, completa todos los campos requeridos', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
    }
  }

  onCancel(): void {
    if (this.magazineId) {
      this.router.navigate(['/magazines', this.magazineId]);
    } else {
      this.router.navigate(['/magazines']);
    }
  }
}
