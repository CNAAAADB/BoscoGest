import { ActivityResponse } from '../models/user.model';

/**
 * When an activity starts and ends, and what that means for the screens that
 * show it. Shared by the list, the detail and the dashboard so that the three
 * agree on whether something is still on.
 *
 * `end_date` is optional: activities created before it existed have none, and
 * a one-off meeting does not need one. Without it, the activity is over as soon
 * as it starts, which is how every screen treated it before.
 */
type ActivityDates = Pick<ActivityResponse, 'date' | 'end_date'>;

export type ActivityStatus = 'upcoming' | 'ongoing' | 'past';

export function activityStart(activity: ActivityDates): Date {
  return new Date(activity.date);
}

export function activityEnd(activity: ActivityDates): Date {
  return activity.end_date ? new Date(activity.end_date) : activityStart(activity);
}

export function activityStatus(activity: ActivityDates, now = new Date()): ActivityStatus {
  if (activityStart(activity) > now) {
    return 'upcoming';
  }
  return activityEnd(activity) > now ? 'ongoing' : 'past';
}

/** Not over yet: either still to come or happening right now. */
export function activityNotFinished(activity: ActivityDates, now = new Date()): boolean {
  return activityStatus(activity, now) !== 'past';
}

function sameDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate();
}

const TIME: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' };

const FORMATS: Record<'long' | 'short', Intl.DateTimeFormatOptions> = {
  long: { year: 'numeric', month: 'long', day: 'numeric', ...TIME },
  short: { day: 'numeric', month: 'short', ...TIME },
};

/**
 * "13 de noviembre de 2026, 17:00 – 15 de noviembre de 2026, 18:00", or with
 * only the closing time when it ends the same day: "…, 10:00 – 14:00".
 */
export function formatActivityDates(activity: ActivityDates, style: 'long' | 'short' = 'long'): string {
  const start = activityStart(activity);
  const from = start.toLocaleString('es-ES', FORMATS[style]);
  if (!activity.end_date) {
    return from;
  }

  const end = new Date(activity.end_date);
  const to = sameDay(start, end)
    ? end.toLocaleTimeString('es-ES', TIME)
    : end.toLocaleString('es-ES', FORMATS[style]);
  return `${from} – ${to}`;
}
