import { CommonModule } from '@angular/common';
import { Component, computed, input, output, signal, OnInit, OnDestroy, effect, inject, HostListener, ChangeDetectionStrategy} from '@angular/core';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { filter, Subscription } from 'rxjs';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { AuthService } from '../auth/auth.service';
import { ViewConfigService, ViewMenuItem } from '../settings/view-config.service';
import { NotificationService } from '../notifications/notification.service';
import { ChatService } from '../chat/chat.service';

export interface MenuItem extends ViewMenuItem {
  separator?: boolean;
  separatorTitle?: string;
  requiresPermission?: { resource: string; action: string };
  /** Platform-wide: the permission has to be held at the root entity. */
  requiresRootPermission?: boolean;
}

@Component({
  selector: 'app-sidebar',
  imports: [RouterModule, CommonModule, MatMenuModule, MatIconModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
,
  changeDetection: ChangeDetectionStrategy.OnPush
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
  private chatService = inject(ChatService);
  unreadCount = this.notificationService.unreadCount;
  chatUnreadCount = this.chatService.totalUnread;

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
        this.viewConfigService.loadStatisticsAvailability().subscribe();
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
      this.viewConfigService.loadStatisticsAvailability().subscribe();
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
      routeLink: 'member-stats',
      icon: 'insights',
      label: 'Estadísticas de socios',
      requiresPermission: { resource: 'users', action: 'manage' }
    },
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
      routeLink: 'membership-requests',
      icon: 'how_to_reg',
      label: 'Solicitudes de alta',
      requiresPermission: { resource: 'memberships', action: 'review' }
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
      routeLink: 'fees/maintenance',
      icon: 'autorenew',
      label: 'Mantenimiento de cuotas',
      requiresPermission: { resource: 'fees', action: 'maintenance' },
      requiresRootPermission: true
    },
    {
      routeLink: 'settings',
      icon: 'settings',
      label: 'Configuración',
      requiresPermission: { resource: 'branding', action: 'update' }
    },
  ];

  // Chat is always visible; only injected if not already in dynamic items
  private readonly chatItem: MenuItem = {
    routeLink: 'chat',
    icon: 'chat',
    label: 'Chat',
  };

  // "Mis cuotas" — injected next to the dynamic "fees" view when it is enabled
  private readonly myFeesItem: MenuItem = {
    routeLink: 'fees/mine',
    icon: 'receipt_long',
    label: 'Mis cuotas',
  };

  // Combined visible items
  visibleItems = computed((): MenuItem[] => {
    const canManageFees = this.authService.hasPermission('fees', 'manage');

    // Expand the dynamic "fees" view: managers keep the admin view and also get
    // "Mis cuotas"; members only get "Mis cuotas" (the admin route is guarded).
    const dynamicItems = this.menuItems().flatMap((item): MenuItem[] => {
      // Statistics is an optional *admin* view, never a public menu entry.
      if (item.routeLink === 'member-stats') return [];
      if (item.routeLink !== 'fees') return [item];
      return canManageFees ? [item, this.myFeesItem] : [this.myFeesItem];
    });

    const hasChatDynamic = dynamicItems.some(item => item.routeLink === 'chat');
    const chatItems: MenuItem[] = hasChatDynamic ? [] : [this.chatItem];

    const adminItemsFiltered = this.adminItems.filter(item => {
      if (item.routeLink === 'member-stats') {
        return this.viewConfigService.statisticsEnabled() &&
          this.authService.canPerform('users', 'manage');
      }
      if (!item.requiresPermission) return true;
      const { resource, action } = item.requiresPermission;
      return item.requiresRootPermission
        ? this.authService.hasRootPermission(resource, action)
        : this.authService.hasPermission(resource, action);
    });

    // Check if any admin items are visible (excluding separator)
    const hasVisibleAdminItems = adminItemsFiltered.some(item => !item.separator);

    if (hasVisibleAdminItems) {
      return [...dynamicItems, ...chatItems, ...adminItemsFiltered];
    }

    return [...dynamicItems, ...chatItems];
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
