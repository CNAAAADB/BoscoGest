import { Component, HostListener, OnInit, signal, computed, ChangeDetectionStrategy} from '@angular/core';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { MainComponent } from '../main/main.component';
import { NativeBottomNavComponent } from '../native-bottom-nav/native-bottom-nav.component';
import { Capacitor } from '@capacitor/core';

@Component({
  selector: 'app-layout',
  imports: [SidebarComponent, MainComponent, NativeBottomNavComponent],
  templateUrl: './layout.component.html',
  styleUrl: './layout.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LayoutComponent implements OnInit {
  /** Native installation only: never show on desktop or mobile browsers. */
  readonly showNativeNavigation = Capacitor.isNativePlatform();
  isLeftSidebarCollapsed = signal<boolean>(false);
  screenWidth = signal<number>(window.innerWidth);
  isMobileView = computed(() => this.screenWidth() <= 768);

  @HostListener('window:resize')
  onResize() {
    this.screenWidth.set(window.innerWidth);
    if (this.screenWidth() < 768) {
      this.isLeftSidebarCollapsed.set(true);
    }
  }

  ngOnInit(): void {
    this.isLeftSidebarCollapsed.set(this.screenWidth() < 768);
  }

  changeIsLeftSidebarCollapsed(isLeftSidebarCollapsed: boolean): void {
    this.isLeftSidebarCollapsed.set(isLeftSidebarCollapsed);
  }
}
