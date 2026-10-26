import { Component, inject, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FormsModule } from '@angular/forms';
import { UsersService } from '../users/users.service';
import { AuthService } from '../auth/auth.service';

/**
 * GDPR data-processing clause, shown on first login right after the forced
 * password change.
 *
 * Consent has to be a deliberate act, so the dialog cannot be dismissed by
 * clicking outside or pressing Escape, the checkbox starts unticked, and
 * declining signs the user out rather than quietly letting them continue.
 */
@Component({
  selector: 'app-consent-dialog',
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './consent-dialog.component.html',
  styleUrl: './consent-dialog.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConsentDialogComponent {
  private dialogRef = inject(MatDialogRef<ConsentDialogComponent>);
  private usersService = inject(UsersService);
  private authService = inject(AuthService);

  loading = signal(true);
  submitting = signal(false);
  accepted = signal(false);
  errorMessage = signal<string | null>(null);

  clauseText = signal<string>('');
  version = signal<string>('');

  constructor() {
    this.usersService.getConsentStatus().subscribe({
      next: (status) => {
        this.version.set(status.current_version);
        this.clauseText.set(status.text ?? '');
        this.loading.set(false);
        // Already accepted the current version — nothing to ask.
        if (status.accepted) {
          this.dialogRef.close(true);
        }
      },
      error: () => {
        this.errorMessage.set(
          'No se ha podido cargar la cláusula de protección de datos. Inténtalo de nuevo.'
        );
        this.loading.set(false);
      },
    });
  }

  /** Renders the clause's **bold** markers without pulling in a markdown library. */
  get paragraphs(): { heading: string; body: string }[] {
    return this.clauseText()
      .split('\n\n')
      .map((block) => block.trim())
      .filter(Boolean)
      .map((block) => {
        const match = block.match(/^\*\*(.+?)\.\*\*\s*([\s\S]*)$/);
        return match
          ? { heading: match[1], body: match[2] }
          : { heading: '', body: block };
      });
  }

  onAccept(): void {
    if (!this.accepted() || this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.errorMessage.set(null);

    this.usersService.acceptConsent(this.version()).subscribe({
      next: () => {
        this.submitting.set(false);
        this.dialogRef.close(true);
      },
      error: (error) => {
        this.submitting.set(false);
        this.errorMessage.set(
          error?.status === 409
            ? 'La cláusula ha cambiado. Recarga la página para revisar la versión actual.'
            : 'No se ha podido registrar tu aceptación. Inténtalo de nuevo.'
        );
      },
    });
  }

  onDecline(): void {
    // Without consent the data cannot be processed, so the session ends.
    this.authService.logout();
    this.dialogRef.close(false);
  }
}
