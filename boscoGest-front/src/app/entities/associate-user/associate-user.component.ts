import { Component, OnInit, signal } from '@angular/core';
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
import { MatRadioModule } from '@angular/material/radio';
import { MatDialog } from '@angular/material/dialog';
import { UsersService } from '../../users/users.service';
import { MembershipsService } from '../../users/memberships.service';
import { EntitiesService } from '../entities.service';
import { UserResponse, RoleResponse } from '../../models/user.model';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { catchError, of } from 'rxjs';

@Component({
  selector: 'app-associate-user',
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
    MatIconModule,
    MatRadioModule
  ],
  templateUrl: './associate-user.component.html',
  styleUrl: './associate-user.component.css'
})
export class AssociateUserComponent implements OnInit {
  searchForm: FormGroup;
  membershipForm: FormGroup;
  loading = signal<boolean>(false);
  searching = signal<boolean>(false);
  entityId: number | null = null;

  // Search results
  foundUser = signal<UserResponse | null>(null);
  userNotFound = signal<boolean>(false);

  // Available roles for the entity
  availableRoles = signal<RoleResponse[]>([]);
  loadingRoles = signal<boolean>(false);

  constructor(
    private fb: FormBuilder,
    private usersService: UsersService,
    private membershipsService: MembershipsService,
    private entitiesService: EntitiesService,
    private router: Router,
    private route: ActivatedRoute,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {
    this.searchForm = this.fb.group({
      searchType: ['email', Validators.required],
      searchValue: ['', Validators.required]
    });

    this.membershipForm = this.fb.group({
      role_id: [null, Validators.required]
    });
  }

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.entityId = parseInt(id, 10);
      this.loadEntityRoles(this.entityId);
    } else {
      this.snackBar.open('ID de entidad no válido', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      this.router.navigate(['/entities']);
    }
  }

  loadEntityRoles(entityId: number): void {
    this.loadingRoles.set(true);
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

  searchUser(): void {
    if (this.searchForm.invalid) {
      return;
    }

    const searchType = this.searchForm.value.searchType;
    const searchValue = this.searchForm.value.searchValue.trim();

    if (!searchValue) {
      this.snackBar.open('Por favor ingrese un valor de búsqueda', 'Cerrar', {
        duration: 3000,
        panelClass: 'error-snackbar'
      });
      return;
    }

    this.searching.set(true);
    this.foundUser.set(null);
    this.userNotFound.set(false);

    const searchObservable = searchType === 'email'
      ? this.usersService.searchUserByEmail(searchValue)
      : this.usersService.searchUserByDni(searchValue);

    searchObservable.pipe(
      catchError((error) => {
        if (error.status === 404) {
          this.userNotFound.set(true);
          this.searching.set(false);
          return of(null);
        }
        throw error;
      })
    ).subscribe({
      next: (user) => {
        if (user) {
          this.foundUser.set(user);
          this.userNotFound.set(false);
        }
        this.searching.set(false);
      },
      error: (error) => {
        console.error('Error searching user:', error);
        this.snackBar.open('Error al buscar el usuario', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.searching.set(false);
      }
    });
  }

  createMembership(): void {
    if (this.membershipForm.invalid || !this.foundUser() || !this.entityId) {
      return;
    }

    this.loading.set(true);
    const membershipData = {
      user_id: this.foundUser()!.id,
      entity_id: this.entityId,
      role_id: this.membershipForm.value.role_id
    };

    this.membershipsService.createMembership(membershipData).subscribe({
      next: () => {
        this.snackBar.open('Usuario asociado correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
        this.router.navigate(['/entities', this.entityId]);
      },
      error: (error) => {
        console.error('Error creating membership:', error);
        const errorMessage = error?.error?.detail || 'Error al asociar el usuario';
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.loading.set(false);
      }
    });
  }

  createNewUser(): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '600px',
      maxWidth: '90vw',
      autoFocus: false,
      restoreFocus: false,
      data: {
        title: 'Crear nuevo usuario',
        message: '¿Desea crear un nuevo usuario desde cero?',
        confirmText: 'Crear',
        cancelText: 'Cancelar'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result && this.entityId) {
        // Navigate to user creation form with entity preloaded
        this.router.navigate(['/users/new'], {
          queryParams: { entityId: this.entityId }
        });
      }
    });
  }

  resetSearch(): void {
    this.foundUser.set(null);
    this.userNotFound.set(false);
    this.searchForm.reset({ searchType: 'email', searchValue: '' });
    this.membershipForm.reset();
  }

  goBack(): void {
    if (this.entityId) {
      this.router.navigate(['/entities', this.entityId]);
    } else {
      this.router.navigate(['/entities']);
    }
  }
}
