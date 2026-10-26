import { ChangeDetectionStrategy, Component, DestroyRef, inject } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LoadingService } from './loading';

/**
 * Covers the screen while something is being saved or sent.
 *
 * The cover itself is there from the first moment and stops every tap; the
 * dimming and the spinner only fade in after a short delay, so a quick save
 * does not flash. Keys are stopped too, or Enter on a focused button would
 * send the form again from behind the cover.
 */
@Component({
  selector: 'app-loading-overlay',
  imports: [MatProgressSpinnerModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (loading.busy()) {
      <div class="loading-cover" role="status" aria-live="polite">
        <div class="loading-box">
          <mat-spinner diameter="44"></mat-spinner>
          <span>Un momento…</span>
        </div>
      </div>
    }
  `,
  styles: [`
    .loading-cover {
      position: fixed;
      inset: 0;
      z-index: 10000;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(20, 28, 48, 0.35);
      opacity: 0;
      animation: loading-appear 150ms ease-out 400ms forwards;
      /* Stops taps from the first moment, even while still invisible. */
      pointer-events: all;
      touch-action: none;
    }
    .loading-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
      padding: 1.5rem 2rem;
      border-radius: 16px;
      background: #fff;
      color: #3D4E7C;
      font-size: 1.125rem;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    }
    @keyframes loading-appear {
      to { opacity: 1; }
    }
    @media (prefers-reduced-motion: reduce) {
      .loading-cover { animation-duration: 1ms; }
    }
  `],
})
export class LoadingOverlayComponent {
  protected readonly loading = inject(LoadingService);

  constructor() {
    const document = inject(DOCUMENT);
    const swallow = (event: KeyboardEvent) => {
      if (this.loading.busy() && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    // Capture phase: it has to run before the button or form sees the key.
    document.addEventListener('keydown', swallow, true);
    inject(DestroyRef).onDestroy(() => document.removeEventListener('keydown', swallow, true));
  }
}
