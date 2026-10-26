import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { LOCALE_ID, Provider, EnvironmentProviders } from '@angular/core';
import { DateAdapter, MAT_DATE_FORMATS, MAT_DATE_LOCALE, MAT_NATIVE_DATE_FORMATS } from '@angular/material/core';
import { SpanishDateAdapter } from '../shared/spanish-date-adapter';
import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';

registerLocaleData(localeEs, 'es');

/**
 * Lo que necesita cualquier componente o servicio de esta aplicación para
 * instanciarse en un test.
 *
 * Los specs que genera el CLI arrancan con un TestBed vacío, y aquí casi todo
 * acaba inyectando AuthService, que a su vez necesita HttpClient: sin esto
 * fallan con NG0201 antes siquiera de llegar al assert.
 *
 * `provideHttpClientTesting` va después de `provideHttpClient` a propósito —
 * sustituye el backend por uno de mentira, de modo que las llamadas que hacen
 * los componentes en ngOnInit no salen a la red ni dejan peticiones colgadas.
 */
export function provideAppTesting(): (Provider | EnvironmentProviders)[] {
  return [
    provideHttpClient(),
    provideHttpClientTesting(),
    provideRouter([]),
    // Sin proveedor de animaciones a propósito: @angular/animations no está
    // instalado y la aplicación real tampoco lo provee. Material funciona sin
    // él, y añadirlo aquí haría que los tests corrieran con una configuración
    // que no es la de producción.
    // Mismo locale que la aplicación real: si no, las fechas se renderizan en
    // inglés y un test sobre texto visible pasaría o fallaría por el motivo
    // equivocado.
    { provide: LOCALE_ID, useValue: 'es' },
    { provide: MAT_DATE_LOCALE, useValue: 'es-ES' },
    { provide: DateAdapter, useClass: SpanishDateAdapter },
    { provide: MAT_DATE_FORMATS, useValue: MAT_NATIVE_DATE_FORMATS },
  ];
}
