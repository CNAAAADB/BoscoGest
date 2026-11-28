import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { ResourcesService } from '../resources.service';
import { EntitiesService } from '../../entities/entities.service';
import { CategoryDialogComponent } from '../category-dialog/category-dialog.component';
import {
  EntityResponse,
  ResourceDetails,
  ResourceCategoryResponse,
  ResourceType,
} from '../../models/user.model';

@Component({
  selector: 'app-resource-form',
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
    MatProgressSpinnerModule,
    MatDialogModule,
  ],
  templateUrl: './resource-form.component.html',
  styleUrl: './resource-form.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResourceFormComponent implements OnInit {
  resourceForm: FormGroup;
  entities = signal<EntityResponse[]>([]);
  categories = signal<ResourceCategoryResponse[]>([]);
  selectedFile: File | null = null;
  submitting = signal<boolean>(false);
  loadingEntities = signal<boolean>(true);
  isEditMode = signal<boolean>(false);
  resourceId: number | null = null;
  existingResource = signal<ResourceDetails | null>(null);

  readonly resourceTypes: { value: ResourceType; label: string; icon: string }[] = [
    { value: 'link', label: 'Enlace', icon: 'link' },
    { value: 'document', label: 'Documento', icon: 'description' },
    { value: 'image', label: 'Imagen', icon: 'image' },
    { value: 'video', label: 'Video', icon: 'videocam' },
  ];

  constructor(
    private fb: FormBuilder,
    private resourcesService: ResourcesService,
    private entitiesService: EntitiesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
  ) {
    this.resourceForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      description: ['', [Validators.maxLength(2000)]],
      resource_type: ['link', [Validators.required]],
      url: [''],
      tags: [''],
      entity_id: ['', [Validators.required]],
      category_id: [null],
    });
  }

  ngOnInit(): void {
    this.loadEntities();

    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditMode.set(true);
      this.resourceId = parseInt(id, 10);
      this.loadResource(this.resourceId);
    }

    // Watch entity_id changes to load categories
    this.resourceForm.get('entity_id')?.valueChanges.subscribe(entityId => {
      if (entityId) {
        this.loadCategories(entityId);
      }
    });
  }

  loadEntities(): void {
    this.loadingEntities.set(true);
    this.entitiesService.getEntities().subscribe({
      next: (entities) => {
        this.entities.set(entities);
        this.loadingEntities.set(false);
      },
      error: () => {
        this.snackBar.open('Error al cargar las entidades', 'Cerrar', { duration: 3000 });
        this.loadingEntities.set(false);
      }
    });
  }

  loadCategories(entityId: number): void {
    this.resourcesService.getCategories(entityId).subscribe({
      next: (categories) => this.categories.set(categories),
      error: () => this.categories.set([]),
    });
  }

  loadResource(id: number): void {
    this.resourcesService.getResource(id).subscribe({
      next: (resource) => {
        if (!resource.permissions?.update) {
          this.snackBar.open('No tienes permisos para editar este recurso', 'Cerrar', { duration: 3000 });
          this.router.navigate(['/resources', id]);
          return;
        }
        this.existingResource.set(resource);
        this.resourceForm.patchValue({
          title: resource.title,
          description: resource.description,
          resource_type: resource.resource_type,
          url: resource.url,
          tags: resource.tags,
          entity_id: resource.entity_id,
          category_id: resource.category_id,
        });
        // Disable type change in edit mode
        this.resourceForm.get('resource_type')?.disable();
        this.resourceForm.get('entity_id')?.disable();

        if (resource.entity_id) {
          this.loadCategories(resource.entity_id);
        }
      },
      error: () => {
        this.snackBar.open('Error al cargar el recurso', 'Cerrar', { duration: 3000 });
        this.router.navigate(['/resources']);
      }
    });
  }

  get isFileType(): boolean {
    const type = this.resourceForm.get('resource_type')?.value;
    return type === 'document' || type === 'image';
  }

  get isUrlType(): boolean {
    const type = this.resourceForm.get('resource_type')?.value;
    return type === 'link' || type === 'video';
  }

  get acceptedExtensions(): string {
    const type = this.resourceForm.get('resource_type')?.value;
    if (type === 'document') return '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt';
    if (type === 'image') return '.jpg,.jpeg,.png,.gif,.webp';
    return '';
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];

      const maxSize = 50 * 1024 * 1024; // 50MB
      if (file.size > maxSize) {
        this.snackBar.open('El archivo no puede superar los 50MB', 'Cerrar', { duration: 3000 });
        input.value = '';
        this.selectedFile = null;
        return;
      }

      this.selectedFile = file;
    }
  }

  openCategoryDialog(): void {
    const entityId = this.resourceForm.get('entity_id')?.value;
    if (!entityId) {
      this.snackBar.open('Selecciona primero una entidad', 'Cerrar', { duration: 3000 });
      return;
    }

    this.dialog.open(CategoryDialogComponent, {
      width: '400px',
      data: { entityId },
    }).afterClosed().subscribe(result => {
      if (result) {
        this.loadCategories(entityId);
        this.resourceForm.get('category_id')?.setValue(result.id);
      }
    });
  }

  onSubmit(): void {
    if (this.isEditMode() && !this.existingResource()?.permissions?.update) return;
    if (!this.resourceForm.valid) {
      this.snackBar.open('Por favor, completa todos los campos requeridos', 'Cerrar', { duration: 3000 });
      return;
    }

    if (this.isEditMode()) {
      this.submitUpdate();
    } else {
      this.submitCreate();
    }
  }

  private submitCreate(): void {
    const formValue = this.resourceForm.value;
    const type = formValue.resource_type as ResourceType;

    if (this.isUrlType && !formValue.url) {
      this.snackBar.open('La URL es requerida para este tipo de recurso', 'Cerrar', { duration: 3000 });
      return;
    }

    if (this.isFileType && !this.selectedFile) {
      this.snackBar.open('Selecciona un archivo para subir', 'Cerrar', { duration: 3000 });
      return;
    }

    this.submitting.set(true);

    if (type === 'link' || type === 'video') {
      this.resourcesService.createResourceLink({
        title: formValue.title,
        description: formValue.description || null,
        resource_type: type,
        url: formValue.url,
        tags: formValue.tags || null,
        entity_id: formValue.entity_id,
        category_id: formValue.category_id || null,
      }).subscribe({
        next: (resource) => {
          this.snackBar.open('Recurso creado correctamente', 'Cerrar', { duration: 3000 });
          this.submitting.set(false);
          this.router.navigate(['/resources', resource.id]);
        },
        error: () => {
          this.snackBar.open('Error al crear el recurso', 'Cerrar', { duration: 3000 });
          this.submitting.set(false);
        }
      });
    } else {
      this.resourcesService.createResourceFile({
        title: formValue.title,
        description: formValue.description || null,
        resource_type: type,
        tags: formValue.tags || null,
        entity_id: formValue.entity_id,
        category_id: formValue.category_id || null,
        file: this.selectedFile!,
      }).subscribe({
        next: (resource) => {
          this.snackBar.open('Recurso subido correctamente', 'Cerrar', { duration: 3000 });
          this.submitting.set(false);
          this.router.navigate(['/resources', resource.id]);
        },
        error: () => {
          this.snackBar.open('Error al subir el recurso', 'Cerrar', { duration: 3000 });
          this.submitting.set(false);
        }
      });
    }
  }

  private submitUpdate(): void {
    const formValue = this.resourceForm.getRawValue();
    this.submitting.set(true);

    this.resourcesService.updateResource(this.resourceId!, {
      title: formValue.title,
      description: formValue.description || null,
      url: formValue.url || null,
      tags: formValue.tags || null,
      category_id: formValue.category_id || null,
    }).subscribe({
      next: () => {
        this.snackBar.open('Recurso actualizado correctamente', 'Cerrar', { duration: 3000 });
        this.submitting.set(false);
        this.router.navigate(['/resources', this.resourceId]);
      },
      error: () => {
        this.snackBar.open('Error al actualizar el recurso', 'Cerrar', { duration: 3000 });
        this.submitting.set(false);
      }
    });
  }

  goBack(): void {
    if (this.isEditMode() && this.resourceId) {
      this.router.navigate(['/resources', this.resourceId]);
    } else {
      this.router.navigate(['/resources']);
    }
  }
}
