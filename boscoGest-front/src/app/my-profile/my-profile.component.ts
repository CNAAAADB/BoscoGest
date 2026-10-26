import { Component, computed, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../auth/auth.service';
import { MembershipDetails } from '../models/user.model';
import { UsersService } from '../users/users.service';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { ConfirmDialogComponent, ConfirmDialogData } from '../confirm-dialog/confirm-dialog.component';
import { ChangePasswordDialogComponent } from '../change-password-dialog/change-password-dialog.component';
import { DeleteAccountDialogComponent } from '../delete-account-dialog/delete-account-dialog.component';

@Component({
  selector: 'app-my-profile',
  imports: [CommonModule, MatCardModule, MatIconModule, MatListModule, MatChipsModule, MatButtonModule, MatDialogModule, MatTooltipModule],
  templateUrl: './my-profile.component.html',
  styleUrl: './my-profile.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MyProfileComponent implements OnInit {
  currentUser = computed(() => this.authService.getCurrentUser());
  currentMembership = computed(() => this.authService.getCurrentMembership());
  // Signal: filled from a subscribe callback; a plain field would leave
  // the memberships list empty under OnPush.
  allMemberships = signal<MembershipDetails[]>([]);

  // Local override so the photo updates immediately after upload
  uploadedPhoto = signal<string | null>(null);
  photoUrl = computed(() => this.uploadedPhoto() ?? this.currentUser()?.photo ?? null);
  uploadingPhoto = signal<boolean>(false);

  constructor(
    private authService: AuthService,
    private http: HttpClient,
    private dialog: MatDialog,
    private usersService: UsersService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadAllMemberships();
  }

  private loadAllMemberships(): void {
    this.http.get<MembershipDetails[]>(`${environment.apiUrl}/memberships`).subscribe({
      next: (memberships) => {
        // Mock memberships para ver diseño
        // const mockMemberships: MembershipDetails[] = [
        //   {
        //     id: 9999,
        //     user_id: 1,
        //     role_id: 2,
        //     entity_id: 100,
        //     is_active: false,
        //     is_current: false,
        //     created_at: '2020-03-15T10:00:00Z',
        //     user: null,
        //     role: {
        //       id: 2,
        //       name: 'Voluntario',
        //       created_at: '2020-01-01T00:00:00Z'
        //     },
        //     entity: {
        //       id: 100,
        //       name: 'Asociación San Pedro',
        //       level: 2,
        //       parent_id: 1,
        //       created_at: '2020-01-01T00:00:00Z'
        //     }
        //   },
        //   {
        //     id: 9998,
        //     user_id: 1,
        //     role_id: 3,
        //     entity_id: 101,
        //     is_active: false,
        //     is_current: false,
        //     created_at: '2018-06-20T10:00:00Z',
        //     user: null,
        //     role: {
        //       id: 3,
        //       name: 'Colaborador',
        //       created_at: '2020-01-01T00:00:00Z'
        //     },
        //     entity: {
        //       id: 101,
        //       name: 'Don Bosco Madrid Centro',
        //       level: 3,
        //       parent_id: 100,
        //       created_at: '2020-01-01T00:00:00Z'
        //     }
        //   },
        //   {
        //     id: 9997,
        //     user_id: 1,
        //     role_id: 1,
        //     entity_id: 102,
        //     is_active: false,
        //     is_current: false,
        //     created_at: '2015-09-10T10:00:00Z',
        //     user: null,
        //     role: {
        //       id: 1,
        //       name: 'Miembro',
        //       created_at: '2020-01-01T00:00:00Z'
        //     },
        //     entity: {
        //       id: 102,
        //       name: 'Grupo Juvenil Salesiano',
        //       level: 4,
        //       parent_id: 101,
        //       created_at: '2020-01-01T00:00:00Z'
        //     }
        //   }
        // ];
        // this.allMemberships.set([...memberships, ...mockMemberships]);
        this.allMemberships.set([...memberships]);
      },
      error: (error) => {
        console.error('Error loading memberships:', error);
      }
    });
  }

  formatDate(dateString: string | null | undefined): string {
    // A birthdate is a calendar day ("1950-01-15"), not an instant: read it as
    // that local day, and say so when there is none instead of "Invalid Date".
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(dateString ?? '');
    if (!match) {
      return 'No especificada';
    }
    const date = new Date(+match[1], +match[2] - 1, +match[3]);
    return date.toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  getLevelName(level: number): string {
    const levelMap: { [key: number]: string } = {
      1: 'Superentity',
      2: 'Confederación',
      3: 'Federación',
      4: 'Asociación Local'
    };
    return levelMap[level] || `Nivel ${level}`;
  }

  onPhotoSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;
    const file = input.files[0];
    if (!file.type.startsWith('image/')) {
      this.snackBar.open('El archivo debe ser una imagen', 'Cerrar', { duration: 3000 });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.snackBar.open('La imagen no puede superar los 5 MB', 'Cerrar', { duration: 3000 });
      return;
    }

    this.uploadingPhoto.set(true);
    this.usersService.uploadMyPhoto(file).subscribe({
      next: (user) => {
        this.uploadingPhoto.set(false);
        this.uploadedPhoto.set(user.photo);
        this.snackBar.open('Foto actualizada correctamente', 'Cerrar', {
          duration: 3000,
          panelClass: 'success-snackbar'
        });
      },
      error: () => {
        this.uploadingPhoto.set(false);
        this.snackBar.open('Error al subir la foto', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
      }
    });
  }

  /**
   * Borrado de la propia cuenta.
   *
   * Vive aquí, en el perfil, porque es donde se busca: Google Play pide que la
   * eliminación esté accesible dentro de la app para cualquier aplicación con
   * registro público.
   */
  openDeleteAccountDialog(): void {
    const dialogRef = this.dialog.open(DeleteAccountDialogComponent, {
      width: '520px',
      disableClose: true
    });

    dialogRef.afterClosed().subscribe(deleted => {
      if (deleted) {
        this.snackBar.open('Tu cuenta ha sido eliminada', 'Cerrar', {
          duration: 5000
        });
        // El token ya está revocado en el servidor, así que aquí solo queda
        // limpiar la sesión local y volver al login.
        this.authService.endSession();
      }
    });
  }

  openChangePasswordDialog(): void {
    const dialogRef = this.dialog.open(ChangePasswordDialogComponent, {
      width: '500px',
      disableClose: false
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        // La contraseña se cambió exitosamente
        // El snackbar ya se muestra en el componente del diálogo
      }
    });
  }

}
