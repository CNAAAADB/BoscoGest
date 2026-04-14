import { CommonModule } from '@angular/common';
import { Component, computed, input, output, signal, OnInit, OnDestroy, effect, inject, HostListener } from '@angular/core';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { filter, Subscription } from 'rxjs';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../auth/auth.service';
import { ViewConfigService, ViewMenuItem } from '../settings/view-config.service';
import { NotificationService } from '../notifications/notification.service';

export interface MenuItem extends ViewMenuItem {
  separator?: boolean;
  separatorTitle?: string;
  requiresPermission?: { resource: string; action: string };
}

@Component({
  selector: 'app-sidebar',
  imports: [RouterModule, CommonModule, MatMenuModule, MatIconModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent implements OnInit, OnDestroy {
  isLeftSidebarCollapsed = input.required<boolean>();
  isMobileView = input.required<boolean>();
  changeIsLeftSidebarCollapsed = output<boolean>();

  // Mobile menu state
  isMobileMenuOpen = signal(false);
  private routerSub?: Subscription;

  // User info
  currentUser = computed(() => this.authService.getCurrentUser());
  currentMembership = computed(() => this.authService.getCurrentMembership());

  userInitial = computed(() => {
    const user = this.currentUser();
    return user ? user.name.charAt(0).toUpperCase() : '?';
  });

  fullName = computed(() => {
    const user = this.currentUser();
    return user ? `${user.name} ${user.surname}` : 'Usuario';
  });

  entityName = computed(() => {
    const membership = this.currentMembership();
    return membership?.entity?.name || 'Sin asociación';
  });

  private notificationService = inject(NotificationService);
  unreadCount = this.notificationService.unreadCount;

  constructor(
    private authService: AuthService,
    private viewConfigService: ViewConfigService,
    private router: Router
  ) {
    // React to entity changes to reload view configs
    effect(() => {
      const membership = this.currentMembership();
      if (membership?.entity_id) {
        this.viewConfigService.loadViewConfigs(membership.entity_id).subscribe();
      }
    });

    // Lock body scroll when mobile menu is open
    effect(() => {
      if (this.isMobileView() && this.isMobileMenuOpen()) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    });

    // Close mobile menu when switching to desktop
    effect(() => {
      if (!this.isMobileView()) {
        this.isMobileMenuOpen.set(false);
      }
    });
  }

  ngOnInit(): void {
    // Load view configs if we already have an entity
    const membership = this.currentMembership();
    if (membership?.entity_id) {
      this.viewConfigService.loadViewConfigs(membership.entity_id).subscribe();
    }

    // Close mobile menu on navigation
    this.routerSub = this.router.events
      .pipe(filter(event => event instanceof NavigationEnd))
      .subscribe(() => this.isMobileMenuOpen.set(false));
  }

  ngOnDestroy(): void {
    this.routerSub?.unsubscribe();
    document.body.style.overflow = '';
  }

  @HostListener('document:keydown.escape')
  onEscapeKey(): void {
    if (this.isMobileView() && this.isMobileMenuOpen()) {
      this.closeMobileMenu();
    }
  }

  navigateToProfile(): void {
    this.router.navigate(['/my-profile']);
  }

  navigateToNotifications(): void {
    this.router.navigate(['/notifications']);
  }

  logout(): void {
    this.authService.logout();
  }

  // Dynamic menu items from ViewConfigService
  menuItems = computed((): MenuItem[] => this.viewConfigService.getMenuItems());

  // Admin items that are always shown to users with permissions
  adminItems: MenuItem[] = [
    { separator: true, separatorTitle: 'Admin', routeLink: '', icon: '', label: '' },
    {
      routeLink: 'users',
      icon: 'manage_accounts',
      label: 'Usuarios',
      requiresPermission: { resource: 'users', action: 'manage' }
    },
    {
      routeLink: 'users/import',
      icon: 'upload_file',
      label: 'Importar Usuarios',
      requiresPermission: { resource: 'users', action: 'create' }
    },
    {
      routeLink: 'roles',
      icon: 'admin_panel_settings',
      label: 'Roles',
      requiresPermission: { resource: 'roles', action: 'manage' }
    },
    {
      routeLink: 'communications',
      icon: 'edit_note',
      label: 'Comunicaciones',
      requiresPermission: { resource: 'communications', action: 'create' }
    },
    {
      routeLink: 'settings',
      icon: 'settings',
      label: 'Configuración',
      requiresPermission: { resource: 'branding', action: 'update' }
    },
  ];

  // Combined visible items
  visibleItems = computed((): MenuItem[] => {
    const dynamicItems = this.menuItems();
    const adminItemsFiltered = this.adminItems.filter(item => {
      if (!item.requiresPermission) return true;
      const { resource, action } = item.requiresPermission;
      return this.authService.hasPermission(resource, action);
    });

    // Check if any admin items are visible (excluding separator)
    const hasVisibleAdminItems = adminItemsFiltered.some(item => !item.separator);

    if (hasVisibleAdminItems) {
      return [...dynamicItems, ...adminItemsFiltered];
    }

    return dynamicItems;
  });

  toggleCollapse(): void {
    this.changeIsLeftSidebarCollapsed.emit(!this.isLeftSidebarCollapsed());
  }

  closeSidenav(): void {
    this.changeIsLeftSidebarCollapsed.emit(true);
  }

  toggleMobileMenu(): void {
    this.isMobileMenuOpen.update(v => !v);
  }

  closeMobileMenu(): void {
    this.isMobileMenuOpen.set(false);
  }
}
