import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FullCalendarModule } from '@fullcalendar/angular';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import esLocale from '@fullcalendar/core/locales/es';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivitiesService } from '../activities.service';
import { ActivityResponse } from '../../models/user.model';

export function activitiesAsCalendarEvents(activities: ActivityResponse[]): EventInput[] {
  return activities.map(activity => ({
    id: String(activity.id),
    title: activity.title,
    start: activity.date,
    // FullCalendar treats event.end as exclusive for all-day events; using
    // timed dates respects the real start/end stored by BoscoGest.
    end: activity.end_date ?? undefined,
    allDay: false,
  }));
}

@Component({
  selector: 'app-activities-calendar',
  standalone: true,
  imports: [FullCalendarModule, MatProgressSpinnerModule],
  templateUrl: './activities-calendar.component.html',
  styleUrl: './activities-calendar.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActivitiesCalendarComponent implements OnInit {
  private readonly activitiesService = inject(ActivitiesService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);
  readonly loading = signal(true);
  readonly calendarOptions = signal<CalendarOptions>({
    plugins: [dayGridPlugin, interactionPlugin],
    initialView: 'dayGridMonth',
    locale: esLocale,
    firstDay: 1,
    height: 'auto',
    displayEventTime: false,
    dayMaxEvents: 2,
    headerToolbar: { left: 'prev,next', center: 'title', right: 'today' },
    buttonText: { today: 'Hoy' },
    events: [],
    eventClick: info => {
      this.router.navigate(['/activities', Number(info.event.id)]);
    }
  });

  ngOnInit(): void {
    this.activitiesService.getActivities().subscribe({
      next: activities => {
        this.calendarOptions.update(options => ({
          ...options,
          events: activitiesAsCalendarEvents(activities),
        }));
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.snackBar.open('No se pudo cargar el calendario', 'Cerrar', { duration: 4000 });
      },
    });
  }
}
