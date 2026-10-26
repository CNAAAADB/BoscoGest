import { Component, OnInit, computed, inject, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ConfirmDialogComponent } from '../../confirm-dialog/confirm-dialog.component';
import { ConsentClause } from '../../models/user.model';
import { ConsentClausesService } from '../consent-clauses.service';

/**
 * Authoring the GDPR data-processing clause.
 *
 * Published versions are immutable by design: rewriting text members already
 * accepted would destroy the record of what they agreed to. Changing the terms
 * means publishing a new version, which asks everyone again on their next
 * login — so publishing is deliberately behind a confirmation that says so.
 */
@Component({
  selector: 'app-consent-clauses',
  imports: [
    CommonModule,
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
  ],
  templateUrl: './consent-clauses.component.html',
  styleUrl: './consent-clauses.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConsentClausesComponent implements OnInit {
  private service = inject(ConsentClausesService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  clauses = signal<ConsentClause[]>([]);
  loading = signal(true);
  saving = signal(false);
  pending = signal<number | null>(null);

  published = computed(() => this.clauses().find((c) => c.is_published) ?? null);
  drafts = computed(() => this.clauses().filter((c) => !c.is_published));

  // New version form
  showNewForm = signal(false);
  newVersion = signal('');
  newText = signal('');

  // Draft being edited, if any
  editingId = signal<number | null>(null);
  editingText = signal('');

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.service.list().subscribe({
      next: (clauses) => {
        this.clauses.set(clauses);
        this.loading.set(false);
      },
      error: () => {
        this.notifyError('No se han podido cargar las versiones de la cláusula');
        this.loading.set(false);
      },
    });
    this.service.pendingCount().subscribe({
      next: (result) => this.pending.set(result.pending),
      error: () => this.pending.set(null),
    });
  }

  /** Prefills the new version with the text in force, so edits start from it. */
  startNewVersion(): void {
    this.newText.set(this.published()?.text ?? '');
    this.newVersion.set(this.suggestNextVersion());
    this.showNewForm.set(true);
  }

  cancelNewVersion(): void {
    this.showNewForm.set(false);
    this.newVersion.set('');
    this.newText.set('');
  }

  private suggestNextVersion(): string {
    const current = this.published()?.version ?? '';
    const match = current.match(/^(\d+)\.(\d+)$/);
    if (!match) {
      return '';
    }
    return `${match[1]}.${Number(match[2]) + 1}`;
  }

  createDraft(publish: boolean): void {
    const version = this.newVersion().trim();
    const text = this.newText().trim();
    if (!version || !text) {
      this.notifyError('Indica una versión y el texto de la cláusula');
      return;
    }
    if (publish) {
      // Publishing forces every member to reaccept, so it goes through the
      // same confirmation as publishing an existing draft.
      this.confirmPublish(version, () => this.submitNewVersion(version, text, true));
      return;
    }
    this.submitNewVersion(version, text, false);
  }

  private submitNewVersion(version: string, text: string, publish: boolean): void {
    this.saving.set(true);
    this.service.create({ version, text, publish }).subscribe({
      next: () => {
        this.saving.set(false);
        this.cancelNewVersion();
        this.notifyOk(
          publish
            ? `Versión ${version} publicada. Se pedirá de nuevo el consentimiento a todos los usuarios.`
            : `Borrador ${version} guardado`
        );
        this.reload();
      },
      error: (error) => {
        this.saving.set(false);
        this.notifyError(
          error?.status === 409
            ? `Ya existe la versión ${version}`
            : 'No se ha podido guardar la versión'
        );
      },
    });
  }

  /** Confirmation shown before any action that puts a version in force. */
  private confirmPublish(version: string, onConfirm: () => void): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '560px',
      maxWidth: '92vw',
      data: {
        title: `Publicar la versión ${version}`,
        message:
          'Esta versión pasará a ser la cláusula en vigor. A todos los usuarios ' +
          'se les volverá a pedir el consentimiento la próxima vez que inicien ' +
          'sesión, y no podrán usar la aplicación hasta que la acepten. ' +
          'Una vez publicada, su texto no podrá modificarse.',
        confirmText: 'Publicar',
        cancelText: 'Cancelar',
      },
    });
    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) {
        onConfirm();
      }
    });
  }

  startEditingDraft(clause: ConsentClause): void {
    this.editingId.set(clause.id);
    this.editingText.set(clause.text);
  }

  cancelEditingDraft(): void {
    this.editingId.set(null);
    this.editingText.set('');
  }

  saveDraft(clause: ConsentClause): void {
    const text = this.editingText().trim();
    if (!text) {
      this.notifyError('El texto no puede quedar vacío');
      return;
    }
    this.saving.set(true);
    this.service.updateDraft(clause.id, text).subscribe({
      next: () => {
        this.saving.set(false);
        this.cancelEditingDraft();
        this.notifyOk('Borrador actualizado');
        this.reload();
      },
      error: () => {
        this.saving.set(false);
        this.notifyError('No se ha podido actualizar el borrador');
      },
    });
  }

  publish(clause: ConsentClause): void {
    this.confirmPublish(clause.version, () => {
      this.saving.set(true);
      this.service.publish(clause.id).subscribe({
        next: () => {
          this.saving.set(false);
          this.notifyOk(`Versión ${clause.version} publicada`);
          this.reload();
        },
        error: () => {
          this.saving.set(false);
          this.notifyError('No se ha podido publicar la versión');
        },
      });
    });
  }

  deleteDraft(clause: ConsentClause): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '520px',
      data: {
        title: `Descartar el borrador ${clause.version}`,
        message: '¿Seguro que quieres descartar este borrador? No se puede deshacer.',
        confirmText: 'Descartar',
        cancelText: 'Cancelar',
      },
    });

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (!confirmed) {
        return;
      }
      this.service.deleteDraft(clause.id).subscribe({
        next: () => {
          this.notifyOk('Borrador descartado');
          this.reload();
        },
        error: (error) => {
          this.notifyError(
            error?.status === 409
              ? 'Esta versión estuvo publicada y no puede eliminarse'
              : 'No se ha podido descartar el borrador'
          );
        },
      });
    });
  }

  private notifyOk(message: string): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 5000,
      panelClass: 'success-snackbar',
    });
  }

  private notifyError(message: string): void {
    this.snackBar.open(message, 'Cerrar', {
      duration: 5000,
      panelClass: 'error-snackbar',
    });
  }
}
