import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AuthService } from '../auth/auth.service';
import { FirstTimePasswordDialogComponent } from '../first-time-password-dialog/first-time-password-dialog.component';

@Component({
  selector: 'app-login',
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  email = signal<string>('');
  password = signal<string>('');
  errorMessage = signal<string>('');

  constructor(
    private authService: AuthService,
    private router: Router,
    private dialog: MatDialog
  ) {}

  onLogin(): void {
    this.authService.login(this.email(), this.password()).subscribe({
      next: (success) => {
        if (success) {
          // Esperar un poco para que se cargue la información del usuario
          setTimeout(() => {
            const currentUser = this.authService.getCurrentUser();

            if (currentUser?.must_change_password) {
              // Mostrar modal no cerrable para cambiar contraseña
              const dialogRef = this.dialog.open(FirstTimePasswordDialogComponent, {
                width: '500px',
                disableClose: true // No se puede cerrar haciendo clic fuera o presionando ESC
              });

              dialogRef.afterClosed().subscribe(result => {
                if (result) {
                  // La contraseña se cambió exitosamente
                  // El diálogo ya redirige al login, no hacemos nada aquí
                } else {
                  // Si por alguna razón se cierra sin éxito, volver a login
                  this.router.navigate(['/login']);
                }
              });
            } else {
              // Si no necesita cambiar contraseña, ir al dashboard
              this.router.navigate(['/dashboard']);
            }
          }, 500);
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
