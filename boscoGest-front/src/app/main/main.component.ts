import { CommonModule } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { BreadcrumbComponent } from '../breadcrumb/breadcrumb.component';

@Component({
  selector: 'app-main',
  imports: [RouterOutlet, CommonModule, BreadcrumbComponent],
  templateUrl: './main.component.html',
  styleUrl: './main.component.css'
})
export class MainComponent {

  isLeftSidebarCollapsed = input.required<boolean>();
  screenWidth = input.required<number>();
  isMobileView = input.required<boolean>();

  sizeClass = computed(() => {
    if (this.isMobileView()) {
      return 'body-mobile';
    }
    const isLeftSidebarCollapsed = this.isLeftSidebarCollapsed();
    if (isLeftSidebarCollapsed) {
      return '';
    }
    return this.screenWidth() > 768 ? 'body-trimmed' : 'body-md-screen';
  });

}
