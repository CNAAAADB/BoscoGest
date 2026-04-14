import { Component, signal, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDialog, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { environment } from '../../../environments/environment';

interface BulkUploadResult {
  total_rows: number;
  successful: number;
  failed: number;
  errors: Array<{
    row: number;
    error: string;
    data: any;
  }>;
  created_users: Array<{
    id: number;
    email: string;
    name: string;
    entity_id: number;
    role_id: number;
  }>;
}

interface CSVField {
  name: string;
  description: string;
  required: boolean;
  example: string;
}

@Component({
  selector: 'app-user-import',
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTableModule,
    MatChipsModule,
    MatSnackBarModule,
    MatExpansionModule,
    MatDialogModule,
    MatTooltipModule
  ],
  templateUrl: './user-import.component.html',
  styleUrl: './user-import.component.css'
})
export class UserImportComponent {
  isUploading = signal<boolean>(false);
  uploadResult = signal<BulkUploadResult | null>(null);
  selectedFile = signal<File | null>(null);

  displayedColumns: string[] = ['row', 'error', 'email', 'actions'];
  displayedSuccessColumns: string[] = ['id', 'name', 'email', 'entity_id', 'actions'];
  csvFieldColumns: string[] = ['field', 'description', 'required', 'example'];

  csvFields: CSVField[] = [
    {
      name: 'email',
      description: 'Correo electrónico del usuario',
      required: true,
      example: 'usuario@ejemplo.com'
    },
    {
      name: 'password',
      description: 'Contraseña temporal (mín. 8 caracteres, 1 mayúscula, 1 número)',
      required: true,
      example: 'Password123'
    },
    {
      name: 'name',
      description: 'Nombre del usuario',
      required: true,
      example: 'Juan'
    },
    {
      name: 'surname',
      description: 'Apellido del usuario',
      required: true,
      example: 'Pérez'
    },
    {
      name: 'phone',
      description: 'Número de teléfono',
      required: true,
      example: '612345678'
    },
    {
      name: 'birthdate',
      description: 'Fecha de nacimiento (formato: YYYY-MM-DD)',
      required: true,
      example: '1990-01-15'
    },
    {
      name: 'dni',
      description: 'DNI/NIF (debe ser único en el sistema)',
      required: true,
      example: '12345678A'
    },
    {
      name: 'entity_id',
      description: 'ID de la asociación a la que pertenece el usuario',
      required: true,
      example: '1'
    },
    {
      name: 'role_id',
      description: 'ID del rol del usuario en la asociación',
      required: true,
      example: '2'
    },
    {
      name: 'address',
      description: 'Dirección postal del usuario',
      required: false,
      example: 'Calle Ejemplo 123'
    },
    {
      name: 'photo',
      description: 'URL de la foto de perfil',
      required: false,
      example: 'https://ejemplo.com/foto.jpg'
    },
    {
      name: 'iban',
      description: 'Número de cuenta bancaria IBAN',
      required: false,
      example: 'ES1234567890123456789012'
    },
    {
      name: 'size',
      description: 'Talla de ropa',
      required: false,
      example: 'M'
    },
    {
      name: 'hobbies',
      description: 'Hobbies e intereses del usuario',
      required: false,
      example: 'Lectura, Deportes'
    },
    {
      name: 'job_position',
      description: 'Puesto de trabajo o profesión',
      required: false,
      example: 'Desarrollador'
    }
  ];

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar,
    private dialog: MatDialog
  ) {}

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];

      // Validar que sea un archivo CSV
      if (!file.name.endsWith('.csv')) {
        this.snackBar.open('Por favor, selecciona un archivo CSV válido', 'Cerrar', {
          duration: 3000,
          panelClass: ['error-snackbar']
        });
        return;
      }

      this.selectedFile.set(file);
      this.uploadResult.set(null);
    }
  }

  uploadFile(): void {
    const file = this.selectedFile();
    if (!file) {
      this.snackBar.open('Por favor, selecciona un archivo primero', 'Cerrar', {
        duration: 3000,
        panelClass: ['error-snackbar']
      });
      return;
    }

    this.isUploading.set(true);
    const formData = new FormData();
    formData.append('file', file);

    this.http.post<BulkUploadResult>(`${environment.apiUrl}/users/bulk-upload`, formData).subscribe({
      next: (result) => {
        this.isUploading.set(false);
        this.uploadResult.set(result);

        if (result.successful > 0) {
          this.snackBar.open(
            `Importación completada: ${result.successful} usuarios creados, ${result.failed} errores`,
            'Cerrar',
            {
              duration: 5000,
              panelClass: ['success-snackbar']
            }
          );
        } else {
          this.snackBar.open(
            'No se pudo crear ningún usuario. Revisa los errores',
            'Cerrar',
            {
              duration: 5000,
              panelClass: ['error-snackbar']
            }
          );
        }
      },
      error: (error: HttpErrorResponse) => {
        this.isUploading.set(false);
        let errorMessage = 'Error al importar usuarios';

        if (error.status === 400) {
          errorMessage = error.error.detail || 'Archivo CSV inválido';
        } else if (error.error?.detail) {
          errorMessage = error.error.detail;
        }

        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 5000,
          panelClass: ['error-snackbar']
        });
      }
    });
  }

  downloadTemplate(): void {
    const csvContent = `"email","password","name","surname","phone","birthdate","dni","entity_id","role_id","address","photo","iban","size","hobbies","job_position"
"usuario@ejemplo.com","Password123","Juan","Pérez","612345678","1990-01-15","12345678A","1","2","Calle Ejemplo 123","","ES1234567890123456789012","M","Lectura, Deportes","Desarrollador"
"maria.garcia@ejemplo.com","Password456","María","García","687654321","1985-05-20","87654321B","1","3","Avenida Principal 456","","ES9876543210987654321098","S","Música, Viajes","Diseñadora"`;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', 'plantilla_usuarios.csv');
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    this.snackBar.open('Plantilla descargada correctamente', 'Cerrar', {
      duration: 3000,
      panelClass: ['success-snackbar']
    });
  }

  clearSelection(): void {
    this.selectedFile.set(null);
    this.uploadResult.set(null);
  }

  viewRowDetails(data: any, type: 'success' | 'error'): void {
    this.dialog.open(RowDetailsDialogComponent, {
      width: '600px',
      data: { rowData: data, type }
    });
  }
}

// Componente de diálogo para mostrar detalles de la fila
@Component({
  selector: 'app-row-details-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>{{ data.type === 'success' ? 'check_circle' : 'error' }}</mat-icon>
      Detalles de la Fila CSV
    </h2>
    <mat-dialog-content>
      <div class="csv-container">
        <div class="csv-row csv-header">{{ getCSVHeader() }}</div>
        <div class="csv-row csv-data">{{ getCSVData() }}</div>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [`
    ::ng-deep .mat-mdc-dialog-container {
      background-color: white !important;
    }

    h2[mat-dialog-title] {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      color: #3D4E7C;
      background-color: white;
    }

    h2[mat-dialog-title] mat-icon {
      color: #D4A76A;
    }

    mat-dialog-content {
      background-color: white;
      overflow: visible;
      padding: 1rem 1.5rem;
    }

    .csv-container {
      background-color: white;
      border: 1px solid #e9ecef;
      border-radius: 4px;
      padding: 1rem;
      font-family: 'Courier New', Courier, monospace;
      font-size: 0.9rem;
      overflow-x: auto;
    }

    .csv-row {
      white-space: nowrap;
      padding: 0.5rem 0;
      color: #495057;
    }

    .csv-header {
      font-weight: 600;
      color: #3D4E7C;
      border-bottom: 2px solid #e9ecef;
      padding-bottom: 0.75rem;
      margin-bottom: 0.75rem;
    }

    .csv-data {
      color: #495057;
    }

    mat-dialog-actions {
      padding: 1rem 1.5rem;
      background-color: white;
    }
  `]
})
export class RowDetailsDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: { rowData: any; type: 'success' | 'error' }) {}

  getCSVHeader(): string {
    const rowData = this.data.type === 'error' ? this.data.rowData.data : this.data.rowData;
    const keys = Object.keys(rowData);
    return keys.map(key => `"${key}"`).join(',');
  }

  getCSVData(): string {
    const rowData = this.data.type === 'error' ? this.data.rowData.data : this.data.rowData;
    const values = Object.values(rowData);
    return values.map(value => `"${value || ''}"`).join(',');
  }
}
