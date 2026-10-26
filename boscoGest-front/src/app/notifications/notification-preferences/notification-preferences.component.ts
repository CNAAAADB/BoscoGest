import { Component, OnInit, signal, inject, ChangeDetectionStrategy} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { NotificationService } from '../notification.service';
import { NotificationPreferenceResponse } from '../../models/user.model';
import { forkJoin } from 'rxjs';

interface PreferenceRow {
  event_type: string;
  label: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
  push_enabled: boolean;
}

@Component({
  selector: 'app-notification-preferences',
  standalone: true,
  imports: [
    CommonModule,
    MatSlideToggleModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './notification-preferences.component.html',
  styleUrl: './notification-preferences.component.css',

  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NotificationPreferencesComponent implements OnInit {
  private notificationService = inject(NotificationService);
  private snackBar = inject(MatSnackBar);

  preferences = signal<PreferenceRow[]>([]);
  loading = signal(true);

  ngOnInit(): void {
    forkJoin({
      eventTypes: this.notificationService.getEventTypes(),
      prefs: this.notificationService.getPreferences(),
    }).subscribe({
      next: ({ eventTypes, prefs }) => {
        const prefMap = new Map<string, NotificationPreferenceResponse>();
        prefs.forEach((p) => prefMap.set(p.event_type, p));

        this.preferences.set(
          eventTypes.map((et) => {
            const existing = prefMap.get(et.event_type);
            return {
              event_type: et.event_type,
              label: et.label,
              in_app_enabled: existing ? existing.in_app_enabled : true,
              email_enabled: existing ? existing.email_enabled : true,
              push_enabled: existing ? existing.push_enabled : true,
            };
          })
        );
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snackBar.open('Error al cargar preferencias', 'Cerrar', {
          duration: 3000,
        });
      },
    });
  }

  togglePreference(eventType: string, enabled: boolean): void {
    this.preferences.update((list) =>
      list.map((p) =>
        p.event_type === eventType ? { ...p, in_app_enabled: enabled } : p
      )
    );
    this.savePreferences();
  }

  /**
   * Interruptor aparte del de la aplicación: se puede querer ver el aviso
   * dentro de BoscoGest pero no que suene el móvil a media tarde.
   */
  togglePush(eventType: string, enabled: boolean): void {
    this.preferences.update((list) =>
      list.map((p) =>
        p.event_type === eventType ? { ...p, push_enabled: enabled } : p
      )
    );
    this.savePreferences();
  }

  private savePreferences(): void {
    const data = {
      preferences: this.preferences().map((p) => ({
        event_type: p.event_type,
        in_app_enabled: p.in_app_enabled,
        email_enabled: p.email_enabled,
        push_enabled: p.push_enabled,
      })),
    };

    this.notificationService.updatePreferences(data).subscribe({
      next: () => {
        this.snackBar.open('Preferencias actualizadas', 'Cerrar', {
          duration: 2000,
        });
      },
      error: () => {
        this.snackBar.open('Error al guardar preferencias', 'Cerrar', {
          duration: 3000,
        });
      },
    });
  }
}
