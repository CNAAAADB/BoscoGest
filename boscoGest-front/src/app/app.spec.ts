import { TestBed } from '@angular/core/testing';
import { App } from './app';
import { provideAppTesting } from './testing/test-providers';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideAppTesting()],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    expect(fixture.componentInstance).toBeTruthy();
  });

  // El stub del CLI buscaba aquí un "Hello, boscoGest-front" que esta
  // aplicación nunca ha tenido: su plantilla es solo el router-outlet, y todo
  // lo demás lo pintan las rutas.
  it('monta el router-outlet', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('router-outlet')).not.toBeNull();
  });
});
