import { Component, OnInit, signal, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from '../auth.service';

/** Where someone who forgot their password asks for a link to choose a new one. */
@Component({
  selector: 'app-forgot-password',
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
  ],
  templateUrl: './forgot-password.component.html',
  // Same look as the activation screen: both are reached without a session
  // and end up in the same place.
  styleUrl: '../activate/activate.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ForgotPasswordComponent implements OnInit {
  private router = inject(Router);
  private authService = inject(AuthService);

  identifier = signal('');
  sending = signal(false);
  sent = signal(false);
  message = signal('');

  ngOnInit(): void {
    // The login screen hands over what was typed there, so nobody has to type
    // it twice. Through navigation state rather than the address: it is
    // personal data and would otherwise end up in the browser history.
    const handed = this.router.lastSuccessfulNavigation?.extras.state?.['identifier'];
    if (typeof handed === 'string') {
      this.identifier.set(handed);
    }
  }

  submit(): void {
    const identifier = this.identifier().trim();
    if (!identifier || this.sending()) {
      return;
    }

    this.sending.set(true);
    this.authService.forgotPassword(identifier).subscribe({
      next: (response) => {
        this.sending.set(false);
        this.message.set(response.message);
        this.sent.set(true);
      },
      // The answer never depends on the account, so a failure here can only
      // be the connection; saying so beats pretending it was sent.
      error: () => {
        this.sending.set(false);
        this.message.set('No hemos podido enviar la petición. Comprueba la conexión e inténtalo de nuevo.');
      },
    });
  }
}
