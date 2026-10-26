import { Component, OnInit, OnDestroy, NgZone, ChangeDetectionStrategy} from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { LoadingOverlayComponent } from './shared/loading/loading-overlay.component';
import { Capacitor } from '@capacitor/core';
import { App as CapApp } from '@capacitor/app';
import { StatusBar, Style } from '@capacitor/status-bar';
import type { PluginListenerHandle } from '@capacitor/core';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, LoadingOverlayComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class App implements OnInit, OnDestroy {
  protected readonly title = 'boscoGest-front';
  private backButtonListener?: PluginListenerHandle;

  constructor(private ngZone: NgZone) {}

  async ngOnInit(): Promise<void> {
    if (!Capacitor.isNativePlatform()) return;

    this.backButtonListener = await CapApp.addListener('backButton', ({ canGoBack }) => {
      this.ngZone.run(() => {
        if (canGoBack) {
          window.history.back();
        } else {
          CapApp.exitApp();
        }
      });
    });

    try {
      await StatusBar.setStyle({ style: Style.Light });
      await StatusBar.setBackgroundColor({ color: '#3D4E7C' });
    } catch {
      // StatusBar not available (e.g. older Android WebView)
    }
  }

  async ngOnDestroy(): Promise<void> {
    await this.backButtonListener?.remove();
  }
}
