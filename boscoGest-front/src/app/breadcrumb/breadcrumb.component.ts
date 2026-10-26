import { Component, OnInit, signal, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, NavigationEnd, Router, RouterModule } from '@angular/router';
import { filter } from 'rxjs';

interface Breadcrumb {
  label: string;
  url: string;
}

@Component({
  selector: 'app-breadcrumb',
  imports: [CommonModule, RouterModule],
  templateUrl: './breadcrumb.component.html',
  styleUrl: './breadcrumb.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class BreadcrumbComponent implements OnInit {
  breadcrumbs = signal<Breadcrumb[]>([]);

  constructor(
    private router: Router,
    private activatedRoute: ActivatedRoute
  ) {}

  ngOnInit(): void {
    this.updateBreadcrumbs();

    // Listen to route changes
    this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => {
        this.updateBreadcrumbs();
      });
  }

  private updateBreadcrumbs(): void {
    const breadcrumbs: Breadcrumb[] = [];
    this.buildBreadcrumbs(this.activatedRoute.root, '', breadcrumbs);
    this.breadcrumbs.set(breadcrumbs);
  }

  private buildBreadcrumbs(
    route: ActivatedRoute,
    url: string = '',
    breadcrumbs: Breadcrumb[] = []
  ): void {
    // Get the route's data
    const label = route.snapshot.data['breadcrumb'];

    // Get the route path
    const path = route.snapshot.url.map(segment => segment.path).join('/');

    // Build the URL
    if (path) {
      url += `/${path}`;
    }

    // Add to breadcrumbs if label exists
    if (label) {
      breadcrumbs.push({ label, url });
    }

    // Recursively process children
    if (route.children) {
      for (const child of route.children) {
        this.buildBreadcrumbs(child, url, breadcrumbs);
      }
    }
  }
}
