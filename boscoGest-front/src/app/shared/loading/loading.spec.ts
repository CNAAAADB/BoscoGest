import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpContext, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { BACKGROUND_REQUEST, LoadingService, loadingInterceptor } from './loading';
import { LoadingOverlayComponent } from './loading-overlay.component';

describe('Pantalla de carga', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let loading: LoadingService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([loadingInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    loading = TestBed.inject(LoadingService);
  });

  afterEach(() => backend.verify());

  it('bloquea mientras se guarda algo y se quita al terminar', () => {
    http.post('/x', {}).subscribe();
    expect(loading.busy()).toBeTrue();

    backend.expectOne('/x').flush({});
    expect(loading.busy()).toBeFalse();
  });

  it('se quita también si el guardado falla', () => {
    http.put('/x', {}).subscribe({ error: () => undefined });

    backend.expectOne('/x').flush('no', { status: 500, statusText: 'Error' });

    expect(loading.busy()).toBeFalse();
  });

  it('sigue mientras quede alguna escritura pendiente', () => {
    http.post('/a', {}).subscribe();
    http.delete('/b').subscribe();

    backend.expectOne('/a').flush({});
    expect(loading.busy()).toBeTrue();

    backend.expectOne('/b').flush({});
    expect(loading.busy()).toBeFalse();
  });

  it('no bloquea las lecturas', () => {
    http.get('/x').subscribe();
    expect(loading.busy()).toBeFalse();
    backend.expectOne('/x').flush({});
  });

  it('no bloquea lo que va en segundo plano', () => {
    http.post('/x', {}, { context: new HttpContext().set(BACKGROUND_REQUEST, true) }).subscribe();
    expect(loading.busy()).toBeFalse();
    backend.expectOne('/x').flush({});
  });

  it('muestra la capa y se traga el Intro mientras dura', () => {
    const fixture = TestBed.createComponent(LoadingOverlayComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.loading-cover')).toBeNull();

    http.post('/x', {}).subscribe();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.loading-cover')).not.toBeNull();

    const enter = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true, bubbles: true });
    document.body.dispatchEvent(enter);
    expect(enter.defaultPrevented).toBeTrue();

    backend.expectOne('/x').flush({});
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.loading-cover')).toBeNull();
  });
});
