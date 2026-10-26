import { AfterViewInit, DestroyRef, Directive, ElementRef, Renderer2, inject } from '@angular/core';

/**
 * Opens the phone's date or time picker wherever the field is touched.
 *
 * A Material outline field is about 56px tall, but the <input> inside is only
 * the middle strip. Touching the rest of the box — or the icon beside it —
 * makes Material focus the input from code, and on Android a focus that does
 * not come from touching the input itself never opens the native picker. The
 * field turned blue and nothing else happened, which from the app looked like
 * a broken input.
 *
 * Touches on the input itself are left alone: there the WebView already opens
 * the picker, and opening it twice is worse than not at all.
 */
@Directive({
  selector: 'input[matInput][type="date"], input[matInput][type="time"]',
})
export class NativePickerDirective implements AfterViewInit {
  private readonly input = inject<ElementRef<HTMLInputElement>>(ElementRef).nativeElement;
  private readonly renderer = inject(Renderer2);
  private readonly destroyRef = inject(DestroyRef);

  ngAfterViewInit(): void {
    const field = this.input.closest('mat-form-field');
    if (!field) {
      return;
    }
    const unlisten = this.renderer.listen(field, 'click', (event: MouseEvent) => this.open(event));
    this.destroyRef.onDestroy(unlisten);
  }

  private open(event: MouseEvent): void {
    if (event.target === this.input || this.input.disabled || this.input.readOnly) {
      return;
    }
    try {
      // Needs the user's gesture, which this click is. Missing in WebViews
      // older than Chromium 99; there the field is at least focused.
      this.input.showPicker();
    } catch {
      this.input.focus();
    }
  }
}
