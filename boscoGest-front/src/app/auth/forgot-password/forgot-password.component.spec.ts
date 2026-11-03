import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { ForgotPasswordComponent } from './forgot-password.component';
import { AuthService } from '../auth.service';
import { provideAppTesting } from '../../testing/test-providers';

describe('ForgotPasswordComponent', () => {
  let fixture: ComponentFixture<ForgotPasswordComponent>;
  let component: ForgotPasswordComponent;
  let authService: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ForgotPasswordComponent],
      providers: [provideAppTesting()],
    });
    authService = TestBed.inject(AuthService);
    fixture = TestBed.createComponent(ForgotPasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('pide el enlace y muestra la respuesta del servidor tal cual', () => {
    const spy = spyOn(authService, 'forgotPassword').and.returnValue(
      of({ message: 'Si esa cuenta existe…' })
    );

    component.identifier.set('  ana@example.org ');
    component.submit();
    fixture.detectChanges();

    expect(spy).toHaveBeenCalledWith('ana@example.org');
    expect(component.sent()).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('Si esa cuenta existe…');
  });

  it('sin nada escrito no envía', () => {
    const spy = spyOn(authService, 'forgotPassword');

    component.identifier.set('   ');
    component.submit();

    expect(spy).not.toHaveBeenCalled();
  });

  it('si falla la conexión lo dice en vez de dar por enviado', () => {
    spyOn(authService, 'forgotPassword').and.returnValue(throwError(() => ({ status: 0 })));

    component.identifier.set('ana@example.org');
    component.submit();

    expect(component.sent()).toBeFalse();
    expect(component.message()).toContain('conexión');
  });
});
