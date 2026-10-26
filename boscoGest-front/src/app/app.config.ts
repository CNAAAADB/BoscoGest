import { ApplicationConfig, LOCALE_ID, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';
import { DateAdapter, MAT_DATE_FORMATS, MAT_DATE_LOCALE, MAT_NATIVE_DATE_FORMATS } from '@angular/material/core';
import { authInterceptor } from './auth/auth.interceptor';
import { loadingInterceptor } from './shared/loading/loading';

import { routes } from './app.routes';
import { MatPaginatorIntl } from '@angular/material/paginator';
import { spanishPaginatorIntl } from './shared/paginator-intl';
import { SpanishDateAdapter } from './shared/spanish-date-adapter';

// Angular ships only en-US by default, so the Spanish data has to be
// registered before LOCALE_ID can select it. Without this, dates, numbers and
// currency render in English — the datepicker showed "AUG 2026" and weekday
// initials "S M T W T F S" in an otherwise Spanish application.
registerLocaleData(localeEs, 'es');

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor, loadingInterceptor])),
    // Drives the date, number and currency pipes.
    { provide: LOCALE_ID, useValue: 'es' },
    // Material ships the paginator strings in English with no locale bundle;
    // this is the supported way to replace them, and it covers every
    // mat-paginator at once.
    { provide: MatPaginatorIntl, useFactory: spanishPaginatorIntl },
    // Material's date adapter reads its own token, not LOCALE_ID: the calendar
    // header, month names and first day of the week come from here. Spain
    // starts the week on Monday, which es-ES encodes.
    { provide: MAT_DATE_LOCALE, useValue: 'es-ES' },
    // Once, for the whole app. Components used to import MatNativeDateModule,
    // which brought its own adapter and would override this one.
    { provide: DateAdapter, useClass: SpanishDateAdapter },
    { provide: MAT_DATE_FORMATS, useValue: MAT_NATIVE_DATE_FORMATS },
  ]
};
