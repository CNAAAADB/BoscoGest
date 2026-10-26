import { Component, OnInit, signal, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../auth.service';
import { PostLoginFlowService } from '../post-login-flow.service';

/** What went wrong, which decides what the screen offers next. */
type FailureReason = 'expired' | 'used' | 'invalid' | 'network';

@Component({
  selector: 'app-activate',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './activate.component.html',
  styleUrl: './activate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActivateComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private authService = inject(AuthService);
  private postLoginFlow = inject(PostLoginFlowService);

  /** Nothing to press while this runs — the link is spent on arrival. */
  exchanging = signal(true);

  failure = signal<FailureReason | null>(null);
  failureMessage = signal('');

  /** The address to send a fresh link to, when this one is past saving. */
  identifier = signal('');
  requestingNew = signal(false);
  newLinkSent = signal(false);

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');

    if (!token) {
      this.exchanging.set(false);
      this.fail('invalid', 'Falta el enlace de acceso. Ábrelo desde el correo que recibiste.');
      return;
    }

    this.authService.activateWithToken(token).subscribe({
      next: () => {
        this.exchanging.set(false);
        // Straight into the same sequence a password login goes through: the
        // account still owes a password, so that dialog opens first.
        //
        // Backing out lands on the login screen. The link is already spent by
        // then, so there is nothing to return to here.
        this.postLoginFlow.run(() => this.router.navigate(['/login']));
      },
      error: (error) => {
        this.exchanging.set(false);
        const detail = error?.error?.detail;
        if (detail?.reason) {
          this.fail(detail.reason as FailureReason, detail.message);
        } else {
          this.fail(
            'network',
            'No hemos podido comprobar el enlace. Inténtalo de nuevo en un momento.'
          );
        }
      },
    });
  }

  private fail(reason: FailureReason, message: string): void {
    this.failure.set(reason);
    this.failureMessage.set(message);
  }

  /** Whether asking for a new link is worth offering for this failure. */
  canRequestNewLink(): boolean {
    const reason = this.failure();
    return reason === 'expired' || reason === 'used';
  }

  requestNewLink(): void {
    const identifier = this.identifier().trim();
    if (!identifier || this.requestingNew()) {
      return;
    }

    this.requestingNew.set(true);
    this.authService.resendActivation(identifier).subscribe({
      // The answer is the same either way — on purpose, so this form cannot be
      // used to find out whether an address belongs to a member.
      next: () => {
        this.requestingNew.set(false);
        this.newLinkSent.set(true);
      },
      error: () => {
        this.requestingNew.set(false);
        this.newLinkSent.set(true);
      },
    });
  }
}
