import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { AuthService } from './auth.service';
import { FirstTimePasswordDialogComponent } from '../first-time-password-dialog/first-time-password-dialog.component';
import { ConsentDialogComponent } from '../consent-dialog/consent-dialog.component';
import { CompleteProfileDialogComponent } from '../complete-profile-dialog/complete-profile-dialog.component';

/**
 * What happens after a session opens, wherever it came from.
 *
 * There are two ways in now — a password, or a one-shot link from a welcome
 * email — and both land in the same place: set a password if one is owed,
 * accept the current consent clause, fill in what the profile is missing. The
 * sequence lived inside the login screen until the second entrance appeared;
 * leaving it there would have meant maintaining it twice.
 */
@Injectable({ providedIn: 'root' })
export class PostLoginFlowService {
  private dialog = inject(MatDialog);
  private router = inject(Router);
  private authService = inject(AuthService);

  /**
   * @param onAbandoned where to go if the person backs out of a step they
   *   cannot skip. The login screen sends them back to itself; the activation
   *   screen has to as well, because its link is already spent.
   */
  run(onAbandoned: () => void): void {
    const currentUser = this.authService.getCurrentUser();

    if (currentUser?.must_change_password) {
      const dialogRef = this.dialog.open(FirstTimePasswordDialogComponent, {
        width: '500px',
        disableClose: true,
      });
      dialogRef.afterClosed().subscribe((result) => {
        if (result === 'completeProfile') {
          // Consent comes first: it governs whether the data may be processed
          // at all, so it is asked before inviting the user to supply more of
          // it.
          this.openConsentDialog(() => this.openCompleteProfileDialog(onAbandoned));
        } else if (!result) {
          onAbandoned();
        }
      });
      return;
    }

    if (!this.authService.hasMemberships()) {
      // No active memberships — there may be a request awaiting approval.
      this.router.navigate(['/pending']);
      return;
    }

    // Checked on every login, not only the first: publishing a new version of
    // the clause has to reach people who already signed in once, otherwise
    // versioning it achieves nothing. The dialog closes itself immediately
    // when the current version is already accepted, so this is invisible in
    // the normal case.
    this.openConsentDialog(() => this.router.navigate(['/dashboard']));
  }

  /**
   * Shows the GDPR clause and runs `onAccepted` only if the user agrees.
   */
  private openConsentDialog(onAccepted: () => void): void {
    const dialogRef = this.dialog.open(ConsentDialogComponent, {
      width: '680px',
      maxWidth: '92vw',
      disableClose: true,
      autoFocus: false,
    });

    dialogRef.afterClosed().subscribe((accepted) => {
      if (accepted) {
        onAccepted();
      } else {
        // Declining logs the session out; there is nowhere to go but back.
        this.router.navigate(['/login']);
      }
    });
  }

  private openCompleteProfileDialog(onAbandoned: () => void): void {
    const dialogRef = this.dialog.open(CompleteProfileDialogComponent, {
      width: '500px',
      data: this.authService.getCurrentUser(),
    });
    dialogRef.afterClosed().subscribe(() => {
      if (!this.authService.hasMemberships()) {
        this.router.navigate(['/pending']);
      } else {
        this.router.navigate(['/dashboard']);
      }
    });
  }
}
