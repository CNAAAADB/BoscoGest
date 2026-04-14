import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatSelectModule } from '@angular/material/select';
import { CommunicationsService } from '../communications.service';
import { AuthService } from '../../auth/auth.service';
import { CommunicationCreate, CommunicationUpdate, CommunicationStatus, EntityResponse } from '../../models/user.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-communications-form',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatSelectModule
  ],
  templateUrl: './communications-form.component.html',
  styleUrl: './communications-form.component.css'
})
export class NewsFormComponent implements OnInit {
  newsForm: FormGroup;
  loading = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  communicationId: number | null = null;
  selectedFile: File | null = null;
  imagePreview: string | null = null;
  currentImageUrl: string | null = null;
  uploadingImage = signal<boolean>(false);
  apiUrl = environment.apiUrl;
  availableEntities = signal<EntityResponse[]>([]);

  canPublish = signal<boolean>(false);
  currentStatus = signal<CommunicationStatus>('draft');

  constructor(
    private fb: FormBuilder,
    private newsService: CommunicationsService,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.canPublish.set(this.authService.hasPermission('communications', 'publish'));
    this.newsForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(255)]],
      content: ['', Validators.required],
      entity_id: [null, Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadAvailableEntities();

    const id = this.route.snapshot.paramMap.get('id');
    if (id && id !== 'new') {
      this.communicationId = parseInt(id, 10);
      this.isEditMode.set(true);
      this.loadNews();
    }
  }

  loadAvailableEntities(): void {
    this.newsService.getEntitiesWithCreatePermission().subscribe({
      next: (entities) => {
        this.availableEntities.set(entities);
      },
      error: (error) => {
        console.error('Error loading entities:', error);
        this.snackBar.open('Error al cargar las entidades disponibles', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  loadNews(): void {
    if (!this.communicationId) return;

    this.loading.set(true);
    this.newsService.getNews(this.communicationId).subscribe({
      next: (news) => {
        this.newsForm.patchValue({
          title: news.title,
          content: news.content,
          entity_id: news.entity_id
        });
        this.currentStatus.set(news.status);

        // Set current image if exists
        if (news.image_url) {
          this.currentImageUrl = news.image_url;
        }

        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading news:', error);
        this.snackBar.open('Error al cargar la comunicación', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/communications']);
      }
    });
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        this.snackBar.open('Tipo de archivo no permitido. Use JPG, PNG, GIF o WEBP', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        return;
      }

      // Validate file size (max 5MB)
      const maxSize = 5 * 1024 * 1024;
      if (file.size > maxSize) {
        this.snackBar.open('El archivo es demasiado grande. Tamaño máximo: 5MB', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        return;
      }

      this.selectedFile = file;

      // Generate preview
      const reader = new FileReader();
      reader.onload = () => {
        this.imagePreview = reader.result as string;
      };
      reader.readAsDataURL(file);
    }
  }

  removeImage(): void {
    this.selectedFile = null;
    this.imagePreview = null;
    this.currentImageUrl = null;
  }

  getImageUrl(imageUrl: string | null): string {
    if (!imageUrl) return '';
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }

  saveDraft(): void {
    this.submitWithStatus('draft');
  }

  sendToReview(): void {
    this.submitWithStatus('draft', 'review');
  }

  publishDirectly(): void {
    this.submitWithStatus('published');
  }

  private submitWithStatus(status: CommunicationStatus, transitionTo?: CommunicationStatus): void {
    if (this.newsForm.invalid) return;

    this.loading.set(true);
    const formValue = this.newsForm.value;

    if (this.isEditMode() && this.communicationId) {
      this.updateNews(formValue, transitionTo);
    } else {
      this.createNews(formValue, status, transitionTo);
    }
  }

  private createNews(formValue: any, status: CommunicationStatus, transitionTo?: CommunicationStatus): void {
    const createData: CommunicationCreate = { ...formValue, status };
    this.newsService.createNews(createData).subscribe({
      next: (news) => {
        if (this.selectedFile) {
          this.uploadImage(news.id, () => {
            if (transitionTo) {
              this.doTransition(news.id, transitionTo);
            }
          });
        } else if (transitionTo) {
          this.doTransition(news.id, transitionTo);
        } else {
          this.snackBar.open('Comunicación guardada como borrador', 'Cerrar', {
            duration: 3000, panelClass: 'success-snackbar'
          });
          this.router.navigate(['/communications']);
        }
      },
      error: (error) => {
        console.error('Error creating news:', error);
        this.snackBar.open('Error al crear la comunicación', 'Cerrar', {
          duration: 3000, panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  private updateNews(formValue: any, transitionTo?: CommunicationStatus): void {
    if (!this.communicationId) return;

    const updateData: CommunicationUpdate = formValue;
    this.newsService.updateNews(this.communicationId, updateData).subscribe({
      next: () => {
        if (this.selectedFile) {
          this.uploadImage(this.communicationId!, () => {
            if (transitionTo) {
              this.doTransition(this.communicationId!, transitionTo);
            }
          });
        } else if (transitionTo) {
          this.doTransition(this.communicationId!, transitionTo);
        } else {
          this.snackBar.open('Comunicación actualizada correctamente', 'Cerrar', {
            duration: 3000, panelClass: 'success-snackbar'
          });
          this.router.navigate(['/communications']);
        }
      },
      error: (error) => {
        console.error('Error updating news:', error);
        this.snackBar.open('Error al actualizar la comunicación', 'Cerrar', {
          duration: 3000, panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  private doTransition(id: number, targetStatus: CommunicationStatus): void {
    this.newsService.transitionStatus(id, targetStatus).subscribe({
      next: () => {
        const messages: Record<string, string> = {
          review: 'Comunicación enviada a revisión',
          published: 'Comunicación publicada',
        };
        this.snackBar.open(messages[targetStatus] || 'Estado actualizado', 'Cerrar', {
          duration: 3000, panelClass: 'success-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/communications']);
      },
      error: (error) => {
        console.error('Error transitioning status:', error);
        this.snackBar.open(error.error?.detail || 'Error al cambiar el estado', 'Cerrar', {
          duration: 3000, panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  private uploadImage(communicationId: number, onSuccess?: () => void): void {
    if (!this.selectedFile) return;

    this.uploadingImage.set(true);
    this.newsService.uploadNewsImage(communicationId, this.selectedFile).subscribe({
      next: () => {
        this.uploadingImage.set(false);
        if (onSuccess) {
          onSuccess();
        } else {
          this.loading.set(false);
          const message = this.isEditMode() ? 'Comunicación actualizada correctamente' : 'Comunicación creada correctamente';
          this.snackBar.open(message, 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/communications']);
        }
      },
      error: (error) => {
        console.error('Error uploading image:', error);
        this.uploadingImage.set(false);
        this.loading.set(false);
        this.snackBar.open('Comunicación guardada pero error al subir la imagen', 'Cerrar', {
          duration: 5000,
          panelClass: 'error-snackbar'
        });
        this.router.navigate(['/communications']);
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/communications']);
  }
}
