import { Component, signal, ChangeDetectionStrategy} from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule } from '@angular/material/dialog';
import { AuthService } from '../auth/auth.service';
import { PostLoginFlowService } from '../auth/post-login-flow.service';

@Component({
  selector: 'app-login',
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginComponent {
  identifier = signal<string>('');
  password = signal<string>('');
  errorMessage = signal<string>('');

  constructor(
    private authService: AuthService,
    private router: Router,
    private postLoginFlow: PostLoginFlowService
  ) {}

  onLogin(): void {
    this.authService.login(this.identifier(), this.password()).subscribe({
      next: (success) => {
        if (success) {
          // The sequence after a session opens is shared with the activation
          // links, so it lives in PostLoginFlowService.
          this.postLoginFlow.run(() => this.router.navigate(['/login']));
        } else {
          this.errorMessage.set('Usuario o contraseña incorrectos');
        }
      },
      error: () => {
        this.errorMessage.set('Error al conectar con el servidor');
      }
    });
  }
}
