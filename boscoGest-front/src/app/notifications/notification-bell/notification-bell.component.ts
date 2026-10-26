import { Component, signal, inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { NotificationService } from '../notification.service';
import { NotificationResponse } from '../../models/user.model';

@Component({
  selector: 'app-notification-bell',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './notification-bell.component.html',
  styleUrl: './notification-bell.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NotificationBellComponent {
  private notificationService = inject(NotificationService);
  private router = inject(Router);

  panelOpen = signal(false);
  notifications = this.notificationService.notifications;
  unreadCount = this.notificationService.unreadCount;

  togglePanel(): void {
    const open = !this.panelOpen();
    this.panelOpen.set(open);
    if (open) {
      this.notificationService.loadNotifications();
    }
  }

  closePanel(): void {
    this.panelOpen.set(false);
  }

  markAllRead(): void {
    this.notificationService.markAllAsRead();
  }

  onNotificationClick(notification: NotificationResponse): void {
    if (!notification.is_read) {
      this.notificationService.markAsRead(notification.id);
    }
    this.closePanel();

    const route = this.getRouteForNotification(notification);
    if (route) {
      this.router.navigate(route);
    }
  }

  deleteNotification(event: Event, id: number): void {
    event.stopPropagation();
    this.notificationService.deleteNotification(id);
  }

  getEventIcon(eventType: string): string {
    const icons: Record<string, string> = {
      magazine_published: 'menu_book',
      activity_created: 'event',
      activity_updated: 'edit_calendar',
      registration_accepted: 'check_circle',
      registration_rejected: 'cancel',
      communication_published: 'campaign',
      comment_added: 'comment',
      resource_published: 'folder_open',
      membership_created: 'group_add',
    };
    return icons[eventType] || 'notifications';
  }

  timeAgo(dateStr: string): string {
    const now = new Date();
    const date = new Date(dateStr);
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'ahora';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `hace ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `hace ${hours} h`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `hace ${days} d`;
    const months = Math.floor(days / 30);
    return `hace ${months} mes${months > 1 ? 'es' : ''}`;
  }

  private getRouteForNotification(
    notification: NotificationResponse
  ): string[] | null {
    const { resource_type, resource_id } = notification;
    if (!resource_id) return null;

    const routeMap: Record<string, string> = {
      magazines: '/magazines',
      activities: '/activities',
      communications: '/communications',
      resources: '/resources',
    };

    const base = routeMap[resource_type];
    if (base) return [base, resource_id.toString()];

    if (resource_type === 'memberships') return ['/dashboard'];
    return null;
  }
}
