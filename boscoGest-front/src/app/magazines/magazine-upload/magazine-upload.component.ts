import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MagazinesService } from '../magazines.service';
import { EntitiesService } from '../../entities/entities.service';
import { EntityResponse } from '../../models/user.model';

@Component({
  selector: 'app-magazine-upload',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './magazine-upload.component.html',
  styleUrl: './magazine-upload.component.css'
})
export class MagazineUploadComponent implements OnInit {
  uploadForm: FormGroup;
  entities = signal<EntityResponse[]>([]);
  selectedFile: File | null = null;
  uploading = signal<boolean>(false);
  loadingEntities = signal<boolean>(true);

  constructor(
    private fb: FormBuilder,
    private magazinesService: MagazinesService,
    private entitiesService: EntitiesService,
    private router: Router,
    private snackBar: MatSnackBar
  ) {
    this.uploadForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      collection: ['', [Validators.maxLength(100)]],
      issue_number: ['', [Validators.min(1)]],
      description: ['', [Validators.maxLength(1000)]],
      entity_id: ['', [Validators.required]]
    });
  }

  ngOnInit(): void {
    this.loadEntities();
  }

  loadEntities(): void {
    this.loadingEntities.set(true);
    this.entitiesService.getEntities().subscribe({
      next: (entities) => {
        this.entities.set(entities);
        this.loadingEntities.set(false);
      },
      error: (error) => {
        console.error('Error loading entities:', error);
        this.snackBar.open('Error al cargar las entidades', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loadingEntities.set(false);
      }
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];

      // Validate file type
      if (file.type !== 'application/pdf') {
        this.snackBar.open('Solo se permiten archivos PDF', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        input.value = '';
        this.selectedFile = null;
        return;
      }

      // Validate file size (max 50MB)
      const maxSize = 50 * 1024 * 1024; // 50MB in bytes
      if (file.size > maxSize) {
        this.snackBar.open('El archivo no puede superar los 50MB', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        input.value = '';
        this.selectedFile = null;
        return;
      }

      this.selectedFile = file;
    }
  }

  onSubmit(): void {
    if (this.uploadForm.valid && this.selectedFile) {
      this.uploading.set(true);

      const magazineCreate = {
        ...this.uploadForm.value,
        file: this.selectedFile
      };

      this.magazinesService.createMagazine(magazineCreate).subscribe({
        next: (magazine) => {
          this.snackBar.open('Revista subida correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.uploading.set(false);
          this.router.navigate(['/magazines', magazine.id]);
        },
        error: (error) => {
          console.error('Error uploading magazine:', error);
          this.snackBar.open('Error al subir la revista', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.uploading.set(false);
        }
      });
    } else {
      if (!this.selectedFile) {
        this.snackBar.open('Por favor, selecciona un archivo PDF', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      } else {
        this.snackBar.open('Por favor, completa todos los campos requeridos', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    }
  }

  goBack(): void {
    this.router.navigate(['/magazines']);
  }
}
