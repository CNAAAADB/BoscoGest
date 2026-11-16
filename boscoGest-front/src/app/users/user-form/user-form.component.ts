import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { UsersService } from '../users.service';
import { UserCreate, UserUpdate, EntityResponse, RoleResponse, USER_SIZE_OPTIONS, UserSize } from '../../models/user.model';
import { EntitiesService } from '../../entities/entities.service';

@Component({
  selector: 'app-user-form',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatIconModule,
    MatDatepickerModule,
    MatCheckboxModule,
    MatSelectModule
  ],
  templateUrl: './user-form.component.html',
  styleUrl: './user-form.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UserFormComponent implements OnInit {
  userForm: FormGroup;
  readonly sizeOptions = USER_SIZE_OPTIONS;
  selectedPhotoFile: File | null = null;
  photoPreviewUrl = signal<string | null>(null);
  loading = signal<boolean>(false);
  isEditMode = signal<boolean>(false);
  userId: number | null = null;

  // Entity and role management
  adminEntities = signal<{ id: number; name: string }[]>([]);
  availableRoles = signal<RoleResponse[]>([]);
  loadingRoles = signal<boolean>(false);

  constructor(
    private fb: FormBuilder,
    private usersService: UsersService,
    private entitiesService: EntitiesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.userForm = this.fb.group({
      email: ['', [Validators.email]],
      name: ['', [Validators.required, Validators.minLength(2)]],
      surname: ['', [Validators.required, Validators.minLength(2)]],
      phone: [''],
      address: [''],
      birthdate: ['', Validators.required],
      dni: [''],
      photo: [''],
      iban: [''],
      size: [''],
      hobbies: [''],
      job_position: [''],
      is_active: [true],
      entity_id: [null],
      role_id: [null]
    });
  }

  ngOnInit(): void {
    // Check if we're in edit mode
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.userId = parseInt(id, 10);
      this.isEditMode.set(true);
      this.loadUser(this.userId);
    } else {
      // In create mode, load admin entities
      this.loadAdminEntities();

      // Check for entityId in query params
      const entityIdParam = this.route.snapshot.queryParamMap.get('entityId');
      if (entityIdParam) {
        const preloadEntityId = parseInt(entityIdParam, 10);
        this.userForm.patchValue({ entity_id: preloadEntityId });
        // The valueChanges subscription below will automatically load the roles
      }
    }

    // Listen to entity selection changes to load roles
    this.userForm.get('entity_id')?.valueChanges.subscribe(entityId => {
      if (entityId) {
        this.loadEntityRoles(entityId);
      } else {
        this.availableRoles.set([]);
        this.userForm.get('role_id')?.setValue(null);
      }
    });
  }

  loadAdminEntities(): void {
    // The associations where this person may create users — the same list the
    // bulk import uses. It used to come from /entities/admin, which answers a
    // different question: the ones whose look and menu you can configure.
    // Someone with a role that creates users but does not touch branding would
    // have found the selector empty.
    this.usersService.getCreatableEntities().subscribe({
      next: (entities) => {
        this.adminEntities.set(entities);
      },
      error: (error) => {
        console.error('Error loading admin entities:', error);
        this.snackBar.open('Error al cargar las entidades', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  loadEntityRoles(entityId: number): void {
    this.loadingRoles.set(true);
    this.availableRoles.set([]);
    this.userForm.get('role_id')?.setValue(null);

    this.entitiesService.getEntityRoles(entityId).subscribe({
      next: (roles) => {
        this.availableRoles.set(roles);
        this.loadingRoles.set(false);
      },
      error: (error) => {
        console.error('Error loading entity roles:', error);
        this.snackBar.open('Error al cargar los roles de la entidad', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loadingRoles.set(false);
      }
    });
  }

  loadUser(id: number): void {
    this.loading.set(true);
    this.usersService.getUser(id).subscribe({
      next: (user) => {
        this.userForm.patchValue({
          email: user.email,
          name: user.name,
          surname: user.surname,
          phone: user.phone,
          address: user.address,
          birthdate: user.birthdate,
          dni: user.dni,
          photo: user.photo,
          iban: user.iban,
          size: user.size,
          hobbies: user.hobbies,
          job_position: user.job_position,
          is_active: user.is_active
        });
        this.photoPreviewUrl.set(user.photo);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading user:', error);
        this.snackBar.open('Error al cargar el usuario', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
        this.router.navigate(['/users']);
      }
    });
  }

  private formatDate(date: any): string {
    if (!date) return '';

    // If it's already a string in YYYY-MM-DD format, return it
    if (typeof date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(date)) {
      return date;
    }

    // If it's a Date object or datetime string, convert to YYYY-MM-DD
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private emptyToNull(value: any): string | null {
    return value ? value : null;
  }

  onSubmit(): void {
    if (this.userForm.invalid) {
      return;
    }

    this.loading.set(true);
    const formValue = this.userForm.value;

    if (this.isEditMode() && this.userId) {
      // Update mode
      const userData: UserUpdate = {
        email: this.emptyToNull(formValue.email),
        name: formValue.name,
        surname: formValue.surname,
        phone: this.emptyToNull(formValue.phone),
        address: this.emptyToNull(formValue.address),
        birthdate: this.formatDate(formValue.birthdate) || null,
        dni: this.emptyToNull(formValue.dni),
        iban: this.emptyToNull(formValue.iban),
        size: this.emptyToNull(formValue.size) as UserSize | null,
        hobbies: this.emptyToNull(formValue.hobbies),
        job_position: this.emptyToNull(formValue.job_position),
        is_active: formValue.is_active
      };

      this.usersService.updateUser(this.userId, userData).subscribe({
        next: () => this.uploadPhotoThenFinish(this.userId!, 'Usuario actualizado correctamente'),
        error: (error) => {
          console.error('Error updating user:', error);
          this.snackBar.open('Error al actualizar el usuario', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    } else {
      // Create mode
      const userData: UserCreate = {
        email: this.emptyToNull(formValue.email),
        name: formValue.name,
        surname: formValue.surname,
        phone: this.emptyToNull(formValue.phone),
        address: this.emptyToNull(formValue.address),
        birthdate: this.formatDate(formValue.birthdate),
        dni: formValue.dni,
        iban: this.emptyToNull(formValue.iban),
        size: this.emptyToNull(formValue.size) as UserSize | null,
        hobbies: this.emptyToNull(formValue.hobbies),
        job_position: this.emptyToNull(formValue.job_position),
        entity_id: formValue.entity_id,
        role_id: formValue.role_id
      };

      this.usersService.createUser(userData).subscribe({
        next: (user) => this.uploadPhotoThenFinish(user.id, 'Usuario creado correctamente'),
        error: (error) => {
          console.error('Error creating user:', error);
          this.snackBar.open('Error al crear el usuario', 'Cerrar', {
            duration: 3000,
            panelClass: 'error-snackbar'
          });
          this.loading.set(false);
        }
      });
    }
  }

  /** After the user is saved, upload the selected photo (if any) and leave. */
  private uploadPhotoThenFinish(userId: number, successMessage: string): void {
    const finish = () => {
      this.snackBar.open(successMessage, 'Cerrar', {
        duration: 3000,
        panelClass: 'success-snackbar'
      });
      this.router.navigate(['/users']);
    };

    const file = this.selectedPhotoFile;
    if (!file) {
      finish();
      return;
    }

    this.usersService.uploadUserPhoto(userId, file).subscribe({
      next: () => finish(),
      error: (error) => {
        console.error('Error uploading photo:', error);
        this.snackBar.open('Usuario guardado, pero falló la subida de la foto', 'Cerrar', {
          duration: 4000,
          panelClass: 'error-snackbar'
        });
        this.router.navigate(['/users']);
      }
    });
  }

  onPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      if (!file.type.startsWith('image/')) {
        this.snackBar.open('El archivo debe ser una imagen', 'Cerrar', { duration: 3000 });
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        this.snackBar.open('La imagen no puede superar los 5 MB', 'Cerrar', { duration: 3000 });
        return;
      }
      this.selectedPhotoFile = file;
      this.photoPreviewUrl.set(URL.createObjectURL(file));
    }
  }

  onCancel(): void {
    this.router.navigate(['/users']);
  }
}
