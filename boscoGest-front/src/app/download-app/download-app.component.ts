import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-download-app',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './download-app.component.html',
  styleUrl: './download-app.component.css'
})
export class DownloadAppComponent {
  downloading = signal(false);

  constructor(
    private http: HttpClient,
    private snackBar: MatSnackBar
  ) {}

  downloadApk(): void {
    this.downloading.set(true);
    this.http.get<{ url: string }>(`${environment.apiUrl}/downloads/apk`).subscribe({
      next: (response) => {
        window.open(response.url, '_blank');
        this.downloading.set(false);
      },
      error: () => {
        this.snackBar.open('Error al obtener el enlace de descarga', 'Cerrar', {
          duration: 3000,
          panelClass: 'error-snackbar'
        });
        this.downloading.set(false);
      }
    });
  }
}
