import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { EntitiesService } from '../entities.service';
import { EntityCreate, EntityUpdate, EntityResponse } from '../../models/user.model';

@Component({
  selector: 'app-entity-form',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatIconModule
  ],
  templateUrl: './entity-form.component.html',
  styleUrl: './entity-form.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EntityFormComponent implements OnInit {
  entityForm: FormGroup;
  loading = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  entityId: number | null = null;
  availableEntities = signal<EntityResponse[]>([]);

  getLevelName(level: number): string {
    const levelMap: { [key: number]: string } = {
      1: 'Superentity',
      2: 'Confederación',
      3: 'Federación',
      4: 'Asociación Local'
    };
    return levelMap[level] || `Nivel ${level}`;
  }

  constructor(
    private fb: FormBuilder,
    private entitiesService: EntitiesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.entityForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      parent_id: [null, Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadAvailableEntities();

    // Check if we're in edit mode
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.entityId = parseInt(id, 10);
      this.isEditMode.set(true);
      this.loadEntity(this.entityId);
    }
  }

  loadAvailableEntities(): void {
    this.entitiesService.getEntities().subscribe({
      next: (entities) => {
        // Filter out current entity if in edit mode
        const filtered = this.entityId
          ? entities.filter(e => e.id !== this.entityId)
          : entities;
        this.availableEntities.set(filtered);
      },
      error: (error) => {
        console.error('Error loading entities:', error);
        this.snackBar.open('Error al cargar las asociaciones', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  loadEntity(id: number): void {
    this.loading.set(true);
    this.entitiesService.getEntity(id).subscribe({
      next: (entity) => {
        this.entityForm.patchValue({
          name: entity.name,
          parent_id: entity.parent_id
        });
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading entity:', error);
        this.snackBar.open('Error al cargar la asociación', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/entities']);
      }
    });
  }

  onSubmit(): void {
    if (this.entityForm.invalid) {
      return;
    }

    this.loading.set(true);
    const formValue = this.entityForm.value;

    if (this.isEditMode() && this.entityId) {
      // Update mode
      const entityData: EntityUpdate = {
        name: formValue.name
      };

      this.entitiesService.updateEntity(this.entityId, entityData).subscribe({
        next: () => {
          this.snackBar.open('Asociación actualizada correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/entities']);
        },
        error: (error) => {
          console.error('Error updating entity:', error);
          this.snackBar.open('Error al actualizar la asociación', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    } else {
      // Create mode
      const entityData: EntityCreate = {
        name: formValue.name,
        parent_id: formValue.parent_id
      };

      this.entitiesService.createEntity(entityData).subscribe({
        next: () => {
          this.snackBar.open('Asociación creada correctamente', 'Cerrar', {
            duration: 3000,
            panelClass: 'success-snackbar'
          });
          this.router.navigate(['/entities']);
        },
        error: (error) => {
          console.error('Error creating entity:', error);
          this.snackBar.open('Error al crear la asociación', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    }
  }

  onCancel(): void {
    this.router.navigate(['/entities']);
  }
}
