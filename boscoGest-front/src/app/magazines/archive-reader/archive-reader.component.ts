import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { Subscription } from 'rxjs';
import { MagazinesService } from '../magazines.service';

@Component({
  standalone: true,
  imports: [MatButtonModule, RouterLink],
  template: `
    <main>
      <a mat-button routerLink="/magazines">Volver a Revistas</a>
      <h1>{{ title }}</h1>
      <div class="controls" role="group" aria-label="Controles de lectura">
        <button mat-stroked-button [disabled]="busy() || !previous()" (click)="open(previous()!)">Anterior</button>
        <span aria-live="polite">Página {{ page() }}</span>
        <button mat-stroked-button [disabled]="busy() || !next()" (click)="open(next()!)">Siguiente</button>
        <button mat-stroked-button [disabled]="zoom() <= 100" (click)="zoom.set(zoom() - 25)">Reducir</button>
        <button mat-stroked-button [disabled]="zoom() >= 250" (click)="zoom.set(zoom() + 25)">Ampliar</button>
      </div>
      @if (busy()) { <p role="status">Cargando página…</p> }
      @if (error()) {
        <p role="alert">{{ error() }}</p>
        <button mat-button (click)="open(requested)">Reintentar</button>
      }
      @if (image()) {
        <div class="sheet"><img [src]="image()" [style.width.%]="zoom()" [alt]="title + ', página ' + page()"></div>
      }
    </main>`,
  styles: [`
    main { max-width: 72rem; margin: auto; padding: 1rem; }
    .controls { display: flex; flex-wrap: wrap; gap: .6rem; align-items: center; margin: 1rem 0; }
    .sheet { overflow: auto; background: #eef0f3; }
    img { display: block; max-width: none; height: auto; }
  `]
})
export class ArchiveReaderComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute).snapshot;
  private service = inject(MagazinesService);
  private id = Number(this.route.paramMap.get('id'));
  private request?: Subscription;
  title = [this.route.queryParamMap.get('titulo') || 'Revista', this.route.queryParamMap.get('anio')].filter(Boolean).join(' · ');
  requested = Number(this.route.queryParamMap.get('pagina') || 1);
  page = signal(this.requested);
  previous = signal<number | null>(null);
  next = signal<number | null>(null);
  busy = signal(false);
  error = signal('');
  image = signal('');
  zoom = signal(100);

  ngOnInit() { this.open(this.requested); }

  open(page: number) {
    this.requested = page;
    this.error.set('');
    this.busy.set(true);
    this.request?.unsubscribe();
    this.request = this.service.getArchivePage(this.id, page).subscribe({
      next: response => {
        this.busy.set(false);
        if (!response.body?.size) { this.error.set('La página está vacía.'); return; }
        const old = this.image();
        this.image.set(URL.createObjectURL(response.body));
        if (old) URL.revokeObjectURL(old);
        this.page.set(page);
        this.previous.set(Number(response.headers.get('X-Previous-Page')) || null);
        this.next.set(Number(response.headers.get('X-Next-Page')) || null);
      },
      error: err => {
        this.busy.set(false);
        this.error.set(err.status === 429 ? 'Espera unos segundos antes de pasar de página.'
          : err.status === 403 ? 'Necesitas ser socio activo para leer esta revista.'
          : err.status === 404 ? 'Esta página ya no está disponible.' : 'No se ha podido cargar la página.');
      }
    });
  }

  ngOnDestroy() {
    this.request?.unsubscribe();
    if (this.image()) URL.revokeObjectURL(this.image());
  }
}
