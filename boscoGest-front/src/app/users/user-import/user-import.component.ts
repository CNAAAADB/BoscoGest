import { Component, signal, Inject, OnInit, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDialog, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { environment } from '../../../environments/environment';
import { fetchBlobNative } from '../../utils/native-http.util';

/** El informe que devuelve la comprobación previa, sin importar nada. */
interface ValidationProblem {
  row: number;
  field: string | null;
  code: string;
  message: string;
}

interface ValidationReport {
  filename: string;
  valid: boolean;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  columns: string[];
  missing_columns: string[];
  ignored_columns: string[];
  unknown_columns: string[];
  problems: ValidationProblem[];
  truncated?: boolean;
  summary: { code: string; message: string; count: number }[];
}

interface CreatableEntity {
  id: number;
  name: string;
}

interface AssignableRole {
  id: number;
  name: string;
  description: string | null;
}

export interface BulkUploadJob {
  id: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  csv_filename: string;
  total_rows: number | null;
  processed_rows: number;
  successful: number;
  failed: number;
  errors: Array<{ row: number; error: string; data: any }>;
  created_users: Array<{ id: number; email: string; name: string; entity_id: number; role_id: number }>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  created_by_id: number;
}

interface ImportField {
  name: string;
  description: string;
  required: boolean;
  example: string;
}

/**
 * Most of the people preparing these files open them in Excel and have never
 * knowingly saved a CSV, so the workbook is accepted as it is. The CSV stays
 * for whoever already has one.
 */
const ACCEPTED_EXTENSIONS = ['.xlsx', '.csv'];

/**
 * Columns some older files still carry, all of which the import ignores.
 *
 * The association and the role come from the selectors on this screen. The
 * password is generated and nobody is told it — everyone created here signs in
 * through the link in their welcome email — so a roster of members no longer
 * has to travel with credentials in it.
 */
const IGNORED_CSV_COLUMNS = ['password', 'role_id', 'entity_id'];

@Component({
  selector: 'app-user-import',
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatProgressBarModule,
    MatTableModule,
    MatChipsModule,
    MatSnackBarModule,
    MatExpansionModule,
    MatDialogModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatSelectModule,
  ],
  templateUrl: './user-import.component.html',
  styleUrl: './user-import.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class UserImportComponent implements OnInit {
  isSubmitting = signal<boolean>(false);
  isRefreshing = signal<boolean>(false);
  currentJob = signal<BulkUploadJob | null>(null);
  selectedFile = signal<File | null>(null);
  creatableEntities = signal<CreatableEntity[]>([]);
  selectedEntityId = signal<number | null>(null);
  assignableRoles = signal<AssignableRole[]>([]);
  selectedRoleId = signal<number | null>(null);
  loadingRoles = signal<boolean>(false);

  displayedColumns: string[] = ['row', 'error', 'email', 'actions'];
  displayedSuccessColumns: string[] = ['id', 'name', 'email', 'entity_id', 'actions'];
  fieldColumns: string[] = ['field', 'description', 'required', 'example'];

  /** Columns present in the chosen file that the import will not read. */
  ignoredColumns = signal<string[]>([]);

  /**
   * Result of checking the file without importing it. Nothing is created, so
   * it can be run as many times as it takes to get the file right.
   */
  report = signal<ValidationReport | null>(null);
  validating = signal(false);
  /** Rows are shown in batches: a bad padrón can have hundreds. */
  problemsShown = signal(50);

  /** Same order as the columns of the Excel template. */
  fields: ImportField[] = [
    { name: 'name', description: 'Nombre', required: true, example: 'Juan' },
    { name: 'surname', description: 'Apellidos', required: true, example: 'Pérez' },
    { name: 'birthdate', description: 'Fecha de nacimiento, con el año completo (1950, no 50). También vale 1950-01-15', required: true, example: '15/01/1950' },
    { name: 'dni', description: 'DNI o NIE con la letra. No puede repetirse', required: true, example: '12345678A' },
    { name: 'email', description: 'Correo electrónico. Hace falta el correo o el teléfono (al menos uno)', required: false, example: 'juan@ejemplo.com' },
    { name: 'phone', description: 'Teléfono. Hace falta el correo o el teléfono (al menos uno)', required: false, example: '612345678' },
    { name: 'address', description: 'Dirección postal', required: false, example: 'Calle Ejemplo 123' },
    { name: 'iban', description: 'Cuenta bancaria (IBAN)', required: false, example: 'ES1234567890123456789012' },
    { name: 'size', description: 'Talla de ropa: XS, S, M, L, XL, XXL o XXXL (en Excel, de la lista desplegable)', required: false, example: 'M' },
    { name: 'hobbies', description: 'Aficiones', required: false, example: 'Lectura, Senderismo' },
    { name: 'job_position', description: 'Profesión o puesto de trabajo', required: false, example: 'Jubilado' },
  ];

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.http.get<CreatableEntity[]>(`${environment.apiUrl}/users/creatable-entities`).subscribe({
      next: (entities) => {
        this.creatableEntities.set(entities);
        if (entities.length === 1) {
          this.selectedEntityId.set(entities[0].id);
          this.loadRolesForEntity(entities[0].id);
        }
      },
      error: () => {
        this.snackBar.open('No se pudieron cargar las asociaciones', 'Cerrar', {
          duration: 3000,
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  onEntityChange(entityId: number): void {
    this.selectedEntityId.set(entityId);
    // The report includes clashes against existing users, which depend on the
    // association, so it stops being true when that changes.
    this.report.set(null);
    this.loadRolesForEntity(entityId);
  }

  private loadRolesForEntity(entityId: number): void {
    // The role list depends on the selected association, so reset any
    // previous choice before reloading.
    this.selectedRoleId.set(null);
    this.assignableRoles.set([]);
    this.loadingRoles.set(true);

    this.http
      .get<AssignableRole[]>(`${environment.apiUrl}/users/assignable-roles`, {
        params: { entity_id: entityId.toString() },
      })
      .subscribe({
        next: (roles) => {
          this.assignableRoles.set(roles);
          this.loadingRoles.set(false);
        },
        error: () => {
          this.loadingRoles.set(false);
          this.snackBar.open('No se pudieron cargar los roles de la asociación', 'Cerrar', {
            duration: 3000,
            panelClass: ['error-snackbar'],
          });
        },
      });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      // Cleared so that picking the same file again, once fixed, fires change.
      input.value = '';
      const name = file.name.toLowerCase();
      if (name.endsWith('.xls')) {
        this.snackBar.open(
          'Es un Excel antiguo (.xls). Ábrelo y guárdalo como «Libro de Excel (.xlsx)», o usa la plantilla Excel',
          'Cerrar',
          { duration: 8000, panelClass: ['error-snackbar'] },
        );
        return;
      }
      if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
        this.snackBar.open('Selecciona un archivo Excel (.xlsx) o CSV (.csv)', 'Cerrar', {
          duration: 5000,
          panelClass: ['error-snackbar'],
        });
        return;
      }
      this.selectedFile.set(file);
      this.currentJob.set(null);
      this.report.set(null);
      this.ignoredColumns.set([]);
      // A workbook cannot be peeked at as text; for it, the same warning comes
      // in the report of "Comprobar el archivo".
      if (name.endsWith('.csv')) {
        this.checkForIgnoredColumns(file);
      }
    }
  }

  /**
   * Older files carry entity_id and role_id columns. They are ignored — both
   * come from the selectors on this screen — but silently, so anyone reusing
   * an old export would assume the file decided where each user landed.
   */
  private checkForIgnoredColumns(file: File): void {
    this.ignoredColumns.set([]);

    // Only the header is needed, so read the first slice rather than the file.
    const reader = new FileReader();
    reader.onload = () => {
      const firstLine = String(reader.result || '').split(/\r?\n/)[0];
      const headers = firstLine
        .split(',')
        .map((h) => h.trim().replace(/^"|"$/g, '').toLowerCase());
      this.ignoredColumns.set(
        IGNORED_CSV_COLUMNS.filter((c) => headers.includes(c))
      );
    };
    reader.onerror = () => this.ignoredColumns.set([]);
    reader.readAsText(file.slice(0, 4096));
  }

  /**
   * Check the file and report on it without importing.
   *
   * Deliberately separate from the import: it creates nothing, leaves no job
   * behind, and can be repeated until the file is clean.
   */
  validateFile(): void {
    const file = this.selectedFile();
    const entityId = this.selectedEntityId();
    if (!file || entityId == null || this.validating()) {
      return;
    }

    this.validating.set(true);
    this.report.set(null);
    this.problemsShown.set(50);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('entity_id', entityId.toString());

    this.http
      .post<ValidationReport>(`${environment.apiUrl}/users/bulk-upload/validate`, formData)
      .subscribe({
        next: (report) => {
          this.validating.set(false);
          this.report.set(report);
        },
        error: (error) => {
          this.validating.set(false);
          this.snackBar.open(
            error?.error?.detail || 'No se ha podido comprobar el archivo',
            'Cerrar',
            { duration: 8000, panelClass: ['error-snackbar'] }
          );
        },
      });
  }

  showMoreProblems(): void {
    this.problemsShown.update((n) => n + 100);
  }

  /** Download the report so it can be worked through away from the screen. */
  downloadReport(): void {
    const report = this.report();
    if (!report) {
      return;
    }

    const filas = [
      ['fila', 'columna', 'problema'],
      ...report.problems.map((p) => [String(p.row), p.field ?? '', p.message]),
    ];
    // Quoted and with the BOM Excel needs to read UTF-8 without mangling it.
    const csv = '\ufeff' + filas
      .map((f) => f.map((v) => `"${v.replace(/"/g, '""')}"`).join(','))
      .join('\n');

    this.saveBlob(
      new Blob([csv], { type: 'text/csv;charset=utf-8;' }),
      `errores_${report.filename.replace(/\.(csv|xlsx)$/i, '')}.csv`,
    );
  }

  uploadFile(): void {
    const file = this.selectedFile();
    if (!file) {
      this.snackBar.open('Por favor, selecciona un archivo primero', 'Cerrar', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
      return;
    }

    const entityId = this.selectedEntityId();
    if (entityId == null) {
      this.snackBar.open('Selecciona la asociación de destino', 'Cerrar', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
      return;
    }

    const roleId = this.selectedRoleId();
    if (roleId == null) {
      this.snackBar.open('Selecciona el rol de los usuarios', 'Cerrar', {
        duration: 3000,
        panelClass: ['error-snackbar'],
      });
      return;
    }

    this.isSubmitting.set(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('entity_id', entityId.toString());
    formData.append('role_id', roleId.toString());

    this.http.post<{ job_id: number; status: string }>(`${environment.apiUrl}/users/bulk-upload`, formData).subscribe({
      next: (response) => {
        this.isSubmitting.set(false);
        this.snackBar.open(
          `Proceso iniciado (Job #${response.job_id}). Usa el botón "Actualizar estado" para ver el progreso.`,
          'Cerrar',
          { duration: 6000, panelClass: ['success-snackbar'] },
        );
        this.fetchJobStatus(response.job_id);
      },
      error: (error: HttpErrorResponse) => {
        this.isSubmitting.set(false);
        let errorMessage = 'Error al iniciar la importación';
        if (error.status === 400) {
          errorMessage = error.error.detail || 'El archivo no es válido';
        } else if (error.error?.detail) {
          errorMessage = error.error.detail;
        }
        this.snackBar.open(errorMessage, 'Cerrar', {
          duration: 5000,
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  refreshJobStatus(): void {
    const job = this.currentJob();
    if (!job) return;
    this.fetchJobStatus(job.id);
  }

  private fetchJobStatus(jobId: number): void {
    this.isRefreshing.set(true);
    this.http.get<BulkUploadJob>(`${environment.apiUrl}/users/bulk-upload/${jobId}`).subscribe({
      next: (job) => {
        this.isRefreshing.set(false);
        this.currentJob.set(job);
      },
      error: () => {
        this.isRefreshing.set(false);
        this.snackBar.open('Error al obtener el estado del proceso', 'Cerrar', {
          duration: 3000,
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  isJobActive(): boolean {
    const status = this.currentJob()?.status;
    return status === 'pending' || status === 'running';
  }

  progressPercent(): number {
    const job = this.currentJob();
    if (!job || !job.total_rows) return 0;
    return Math.round((job.processed_rows / job.total_rows) * 100);
  }

  /**
   * The Excel template, built by the backend so its columns are exactly the
   * ones the importer reads. It also carries the date format, the size
   * drop-down and an instructions sheet, none of which a CSV can hold.
   */
  downloadExcelTemplate(): void {
    const url = `${environment.apiUrl}/users/bulk-upload/template.xlsx`;
    fetchBlobNative(url, () => this.http.get(url, { responseType: 'blob' })).subscribe({
      next: (blob) => {
        this.saveBlob(blob, 'plantilla_usuarios.xlsx');
        this.snackBar.open('Plantilla Excel descargada', 'Cerrar', {
          duration: 3000,
          panelClass: ['success-snackbar'],
        });
      },
      error: () => {
        this.snackBar.open('No se ha podido descargar la plantilla', 'Cerrar', {
          duration: 5000,
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  downloadCsvTemplate(): void {
    const csvContent = `"email","phone","name","surname","birthdate","dni","address","iban","size","hobbies","job_position"
"usuario@ejemplo.com","612345678","Juan","Pérez","1990-01-15","12345678A","Calle Ejemplo 123","ES1234567890123456789012","M","Lectura, Deportes","Desarrollador"
"","687654321","María","García","1985-05-20","87654321B","Avenida Principal 456","ES9876543210987654321098","S","Música, Viajes","Diseñadora"`;

    this.saveBlob(new Blob([csvContent], { type: 'text/csv;charset=utf-8;' }), 'plantilla_usuarios.csv');

    this.snackBar.open('Plantilla CSV descargada', 'Cerrar', {
      duration: 3000,
      panelClass: ['success-snackbar'],
    });
  }

  private saveBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  clearSelection(): void {
    this.selectedFile.set(null);
    this.currentJob.set(null);
    this.report.set(null);
    this.ignoredColumns.set([]);
  }

  viewRowDetails(data: any, type: 'success' | 'error'): void {
    this.dialog.open(RowDetailsDialogComponent, {
      width: '600px',
      data: { rowData: data, type },
    });
  }
}

@Component({
  selector: 'app-row-details-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>
      <mat-icon>{{ data.type === 'success' ? 'check_circle' : 'error' }}</mat-icon>
      Detalles de la fila
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
    ::ng-deep .mat-mdc-dialog-container { background-color: white !important; }
    h2[mat-dialog-title] { display: flex; align-items: center; gap: 0.5rem; color: #3D4E7C; background-color: white; }
    h2[mat-dialog-title] mat-icon { color: #D4A76A; }
    mat-dialog-content { background-color: white; overflow: visible; padding: 1rem 1.5rem; }
    .csv-container { background-color: white; border: 1px solid #e9ecef; border-radius: 4px; padding: 1rem; font-family: 'Courier New', Courier, monospace; font-size: 0.9rem; overflow-x: auto; }
    .csv-row { white-space: nowrap; padding: 0.5rem 0; color: #495057; }
    .csv-header { font-weight: 600; color: #3D4E7C; border-bottom: 2px solid #e9ecef; padding-bottom: 0.75rem; margin-bottom: 0.75rem; }
    mat-dialog-actions { padding: 1rem 1.5rem; background-color: white; }
  `],
})
export class RowDetailsDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: { rowData: any; type: 'success' | 'error' }) {}

  getCSVHeader(): string {
    const rowData = this.data.type === 'error' ? this.data.rowData.data : this.data.rowData;
    return Object.keys(rowData).map(key => `"${key}"`).join(',');
  }

  getCSVData(): string {
    const rowData = this.data.type === 'error' ? this.data.rowData.data : this.data.rowData;
    return Object.values(rowData).map(value => `"${value || ''}"`).join(',');
  }
}
