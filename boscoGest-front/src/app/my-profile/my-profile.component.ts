import { Component, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AuthService } from '../auth/auth.service';
import { MembershipDetails } from '../models/user.model';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { ConfirmDialogComponent, ConfirmDialogData } from '../confirm-dialog/confirm-dialog.component';
import { ChangePasswordDialogComponent } from '../change-password-dialog/change-password-dialog.component';

@Component({
  selector: 'app-my-profile',
  imports: [CommonModule, MatCardModule, MatIconModule, MatListModule, MatChipsModule, MatButtonModule, MatDialogModule],
  templateUrl: './my-profile.component.html',
  styleUrl: './my-profile.component.css'
})
export class MyProfileComponent implements OnInit {
  currentUser = computed(() => this.authService.getCurrentUser());
  currentMembership = computed(() => this.authService.getCurrentMembership());
  allMemberships: MembershipDetails[] = [];

  constructor(
    private authService: AuthService,
    private http: HttpClient,
    private dialog: MatDialog
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
        // this.allMemberships = [...memberships, ...mockMemberships];
        this.allMemberships = [...memberships];
      },
      error: (error) => {
        console.error('Error loading memberships:', error);
      }
    });
  }

  formatDate(dateString: string): string {
    const date = new Date(dateString);
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
