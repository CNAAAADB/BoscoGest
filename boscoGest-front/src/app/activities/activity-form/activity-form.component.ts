import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatSelectModule } from '@angular/material/select';
import { ActivitiesService } from '../activities.service';
import { ActivityResponse, EntityResponse } from '../../models/user.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-activity-form',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatSelectModule
  ],
  templateUrl: './activity-form.component.html',
  styleUrl: './activity-form.component.css'
})
export class ActivityFormComponent implements OnInit {
  activityForm: FormGroup;
  loading = signal<boolean>(false);
  isEditMode = false;
  activityId: number | null = null;
  selectedFile: File | null = null;
  imagePreview: string | null = null;
  currentImageUrl: string | null = null;
  apiUrl = environment.apiUrl;
  availableEntities = signal<EntityResponse[]>([]);

  // Separate date and time controls
  dateControl!: FormControl<Date | null>;
  timeControl!: FormControl<string | null>;

  constructor(
    private fb: FormBuilder,
    private activitiesService: ActivitiesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.activityForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      description: ['', Validators.required],
      capacity: [0, [Validators.required, Validators.min(1)]],
      price: [0, [Validators.required, Validators.min(0)]],
      allow_waitlist: [true],
      entity_id: [null, Validators.required]
    });

    // Initialize date and time controls
    this.dateControl = this.fb.control<Date | null>(null, Validators.required);
    this.timeControl = this.fb.control<string | null>('', Validators.required);
  }

  ngOnInit(): void {
    // Load available entities
    this.loadAvailableEntities();

    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode = true;
      this.activityId = parseInt(id, 10);
      this.loadActivity(this.activityId);
    }
  }

  loadAvailableEntities(): void {
    this.activitiesService.getEntitiesWithCreatePermission().subscribe({
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

  loadActivity(id: number): void {
    this.loading.set(true);
    this.activitiesService.getActivity(id).subscribe({
      next: (activity) => {
        this.activityForm.patchValue({
          title: activity.title,
          description: activity.description,
          capacity: activity.capacity,
          price: activity.price,
          allow_waitlist: activity.allow_waitlist,
          entity_id: activity.entity_id
        });

        // Set date and time from activity date
        const activityDate = new Date(activity.date);
        this.dateControl.setValue(activityDate);
        this.timeControl.setValue(this.formatTimeForInput(activityDate));

        // Set current image if exists
        if (activity.image_url) {
          this.currentImageUrl = activity.image_url;
        }

        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading activity:', error);
        this.snackBar.open('Error al cargar la actividad', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/activities']);
      }
    });
  }

  formatTimeForInput(date: Date): string {
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${hours}:${minutes}`;
  }

  combineDateAndTime(): string {
    const date = this.dateControl.value;
    const time = this.timeControl.value;

    if (!date || !time) {
      return '';
    }

    const [hours, minutes] = time.split(':');
    const combined = new Date(date);
    combined.setHours(parseInt(hours, 10));
    combined.setMinutes(parseInt(minutes, 10));
    combined.setSeconds(0);

    return combined.toISOString();
  }

  onFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      this.selectedFile = target.files[0];

      // Create image preview
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imagePreview = e.target?.result as string;
      };
      reader.readAsDataURL(this.selectedFile);
    }
  }

  removeImage(): void {
    this.selectedFile = null;
    this.imagePreview = null;
    this.currentImageUrl = null;
  }

  getImageUrl(imageUrl: string): string {
    if (imageUrl.startsWith('http')) return imageUrl;
    return `${this.apiUrl}${imageUrl}`;
  }

  onSubmit(): void {
    if (this.activityForm.invalid || this.dateControl.invalid || this.timeControl.invalid) {
      this.snackBar.open('Por favor completa todos los campos requeridos', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      return;
    }

    this.loading.set(true);
    const formValue = {
      ...this.activityForm.value,
      date: this.combineDateAndTime()
    };

    if (this.isEditMode && this.activityId) {
      this.activitiesService.updateActivity(this.activityId, formValue).subscribe({
        next: () => {
          // Upload image if selected
          if (this.selectedFile) {
            this.uploadImage(this.activityId!);
          } else {
            this.snackBar.open('Actividad actualizada correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.router.navigate(['/activities', this.activityId]);
          }
        },
        error: (error) => {
          console.error('Error updating activity:', error);
          this.snackBar.open('Error al actualizar la actividad', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    } else {
      this.activitiesService.createActivity(formValue).subscribe({
        next: (activity) => {
          // Upload image if selected
          if (this.selectedFile) {
            this.uploadImage(activity.id);
          } else {
            this.snackBar.open('Actividad creada correctamente', 'Cerrar', {
              duration: 3000,
              panelClass: 'success-snackbar'
            });
            this.router.navigate(['/activities', activity.id]);
          }
        },
        error: (error) => {
          console.error('Error creating activity:', error);
          this.snackBar.open('Error al crear la actividad', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    }
  }

  uploadImage(activityId: number): void {
    if (!this.selectedFile) return;

    this.activitiesService.uploadActivityImage(activityId, this.selectedFile).subscribe({
      next: () => {
        this.snackBar.open(
          this.isEditMode ? 'Actividad e imagen actualizadas correctamente' : 'Actividad e imagen creadas correctamente',
          'Cerrar',
          {
            duration: 3000,
            panelClass: 'success-snackbar'
          }
        );
        this.router.navigate(['/activities', activityId]);
      },
      error: (error) => {
        console.error('Error uploading image:', error);
        this.snackBar.open('Actividad guardada pero error al subir la imagen', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.router.navigate(['/activities', activityId]);
      }
    });
  }

  goBack(): void {
    if (this.isEditMode && this.activityId) {
      this.router.navigate(['/activities', this.activityId]);
    } else {
      this.router.navigate(['/activities']);
    }
  }
}
