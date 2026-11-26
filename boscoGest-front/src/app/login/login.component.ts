import { Component, signal, ChangeDetectionStrategy} from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatDialogModule } from '@angular/material/dialog';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { Capacitor } from '@capacitor/core';
import { SessionCredentialService } from '../auth/session-credential.service';
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
    MatIconModule,
    MatCardModule,
    MatDialogModule,
    MatCheckboxModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginComponent {
  identifier = signal<string>('');
  password = signal<string>('');
  showPassword = signal(false);
  errorMessage = signal<string>('');
  readonly mobileApp = Capacitor.isNativePlatform();
  enableBiometric = signal(false);

  constructor(
    private authService: AuthService,
    private router: Router,
    private postLoginFlow: PostLoginFlowService,
    private credentials: SessionCredentialService
  ) {
    this.enableBiometric.set(this.credentials.biometricEnabled());
  }

  onLogin(): void {
    this.authService.login(this.identifier(), this.password()).subscribe({
      next: (success) => {
        if (success) {
          // The sequence after a session opens is shared with the activation
          // links, so it lives in PostLoginFlowService.
          if (this.mobileApp) {
            void this.credentials.enableBiometrics(this.enableBiometric()).then((enabled) => {
              if (this.enableBiometric() && !enabled) {
                this.errorMessage.set('La biometría no está disponible; puedes seguir usando tu contraseña.');
              }
              this.postLoginFlow.run(() => this.router.navigate(['/login']));
            });
          } else {
            this.postLoginFlow.run(() => this.router.navigate(['/login']));
          }
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
