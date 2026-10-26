import { ChangeDetectionStrategy, Component, Inject, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EntitiesService } from '../../entities/entities.service';
import { MembershipsService } from '../memberships.service';
import { RoleResponse } from '../../models/user.model';

export interface ChangeRoleDialogData {
  membershipId: number;
  entityId: number;
  entityName: string;
  currentRoleName: string;
  userName: string;
}

/**
 * Cambia el rol de una persona dentro de una asociación.
 *
 * Hacía falta porque aceptar una solicitud de alta crea siempre la membresía
 * como `socio`, sin opción a elegir, y hasta ahora no había forma de
 * cambiarlo: el endpoint existía pero ninguna pantalla lo llamaba.
 *
 * Los roles se piden a la asociación concreta, no al catálogo global: cada una
 * tiene los suyos, y ofrecer uno que no le pertenece daría un error del
 * servidor después de haberlo elegido.
 */
@Component({
  selector: 'app-change-role-dialog',
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './change-role-dialog.component.html',
  styleUrl: './change-role-dialog.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChangeRoleDialogComponent {
  private entitiesService = inject(EntitiesService);
  private membershipsService = inject(MembershipsService);
  dialogRef = inject(MatDialogRef<ChangeRoleDialogComponent>);

  roles = signal<RoleResponse[]>([]);
  selectedRoleId = signal<number | null>(null);
  loading = signal(true);
  saving = signal(false);
  errorMessage = signal<string | null>(null);

  constructor(@Inject(MAT_DIALOG_DATA) public data: ChangeRoleDialogData) {
    this.entitiesService.getEntityRoles(data.entityId).subscribe({
      next: (roles) => {
        this.roles.set(roles);
        // Deja preseleccionado el rol actual, para que se vea de dónde parte.
        const actual = roles.find((r) => r.name === data.currentRoleName);
        if (actual) this.selectedRoleId.set(actual.id);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.errorMessage.set(
          'No se han podido cargar los roles de la asociación.'
        );
      },
    });
  }

  /** Sin cambio no se envía nada: ahorra una escritura y una entrada de auditoría. */
  get sinCambios(): boolean {
    const actual = this.roles().find((r) => r.name === this.data.currentRoleName);
    return actual ? this.selectedRoleId() === actual.id : false;
  }

  onSave(): void {
    const roleId = this.selectedRoleId();
    if (roleId === null || this.saving() || this.sinCambios) return;

    this.saving.set(true);
    this.errorMessage.set(null);

    this.membershipsService
      .updateMembership(this.data.membershipId, { role_id: roleId })
      .subscribe({
        next: () => this.dialogRef.close(true),
        error: (error: HttpErrorResponse) => {
          this.saving.set(false);
          this.errorMessage.set(this.messageFor(error));
        },
      });
  }

  onCancel(): void {
    this.dialogRef.close(false);
  }

  private messageFor(error: HttpErrorResponse): string {
    if (error.status === 403) {
      return 'No tienes permiso para cambiar roles en esta asociación.';
    }
    if (error.error?.detail && typeof error.error.detail === 'string') {
      return error.error.detail;
    }
    return 'No se ha podido cambiar el rol. Inténtalo de nuevo.';
  }
}
