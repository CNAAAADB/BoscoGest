import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule } from '@angular/material/icon';
import { MembershipsService, MembershipCreate } from '../memberships.service';
import { EntitiesService } from '../../entities/entities.service';
import { EntityResponse, RoleResponse } from '../../models/user.model';

@Component({
  selector: 'app-membership-form',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatIconModule
  ],
  templateUrl: './membership-form.component.html',
  styleUrl: './membership-form.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MembershipFormComponent implements OnInit {
  membershipForm: FormGroup;
  loading = signal<boolean>(false);
  userId: number | null = null;

  // Entity and role management
  manageableEntities = signal<EntityResponse[]>([]);
  availableRoles = signal<RoleResponse[]>([]);
  loadingRoles = signal<boolean>(false);

  constructor(
    private fb: FormBuilder,
    private membershipsService: MembershipsService,
    private entitiesService: EntitiesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar
  ) {
    this.membershipForm = this.fb.group({
      entity_id: [null, Validators.required],
      role_id: [null, Validators.required]
    });
  }

  ngOnInit(): void {
    // Get user ID from route
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.userId = parseInt(id, 10);
      this.loadManageableEntities();
    } else {
      this.snackBar.open('ID de usuario no válido', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      this.router.navigate(['/users']);
    }

    // Listen to entity selection changes to load roles
    this.membershipForm.get('entity_id')?.valueChanges.subscribe(entityId => {
      if (entityId) {
        this.loadEntityRoles(entityId);
      } else {
        this.availableRoles.set([]);
        this.membershipForm.get('role_id')?.setValue(null);
      }
    });
  }

  loadManageableEntities(): void {
    this.loading.set(true);
    this.entitiesService.getMembershipManageableEntities().subscribe({
      next: (entities) => {
        this.manageableEntities.set(entities);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Error loading manageable entities:', error);
        this.snackBar.open('Error al cargar las entidades', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  loadEntityRoles(entityId: number): void {
    this.loadingRoles.set(true);
    this.availableRoles.set([]);
    this.membershipForm.get('role_id')?.setValue(null);

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

  onSubmit(): void {
    if (this.membershipForm.invalid || !this.userId) {
      return;
    }

    this.loading.set(true);
    const formValue = this.membershipForm.value;

    const membershipData: MembershipCreate = {
      user_id: this.userId,
      entity_id: formValue.entity_id,
      role_id: formValue.role_id
    };

    this.membershipsService.createMembership(membershipData).subscribe({
      next: () => {
        this.snackBar.open('Membresía creada correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.router.navigate(['/users']);
      },
      error: (error) => {
        console.error('Error creating membership:', error);
        const errorMessage = error?.error?.detail || 'Error al crear la membresía';
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  onCancel(): void {
    this.router.navigate(['/users']);
  }
}
