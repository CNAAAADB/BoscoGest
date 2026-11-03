import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';

import { ResetPasswordComponent } from './reset-password.component';
import { AuthService } from '../auth.service';
import { PostLoginFlowService } from '../post-login-flow.service';
import { provideAppTesting } from '../../testing/test-providers';

describe('ResetPasswordComponent', () => {
  let fixture: ComponentFixture<ResetPasswordComponent>;
  let component: ResetPasswordComponent;
  let authService: AuthService;
  let flow: PostLoginFlowService;

  function crear(token: string | null) {
    TestBed.configureTestingModule({
      imports: [ResetPasswordComponent],
      providers: [
        provideAppTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(token ? { token } : {}) } },
        },
      ],
    });
    authService = TestBed.inject(AuthService);
    flow = TestBed.inject(PostLoginFlowService);
    spyOn(flow, 'run');
    fixture = TestBed.createComponent(ResetPasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  function rellenar(a: string, b = a) {
    component.form.setValue({ new_password: a, confirm_password: b });
  }

  it('sin token en el enlace no ofrece el formulario', () => {
    crear(null);

    expect(component.failure()).toBe('invalid');
    expect(fixture.nativeElement.textContent).toContain('Pedir un enlace nuevo');
  });

  it('no envía una contraseña que no cumple las reglas', () => {
    crear('t'.repeat(43));
    const spy = spyOn(authService, 'resetPassword');

    rellenar('corta');
    component.submit();
    rellenar('sinmayuscula1');
    component.submit();
    rellenar('Valida123', 'Otra123');
    component.submit();

    expect(spy).not.toHaveBeenCalled();
  });

  it('envía el enlace con la contraseña y sigue como tras un login', () => {
    crear('t'.repeat(43));
    const spy = spyOn(authService, 'resetPassword').and.returnValue(of(true));

    rellenar('Valida123');
    component.submit();

    expect(spy).toHaveBeenCalledWith('t'.repeat(43), 'Valida123', 'Valida123');
    expect(flow.run).toHaveBeenCalled();
  });

  it('un enlace caducado muestra el motivo y cómo pedir otro', () => {
    crear('t'.repeat(43));
    spyOn(authService, 'resetPassword').and.returnValue(
      throwError(() => ({ error: { detail: { reason: 'expired', message: 'Este enlace ha caducado.' } } }))
    );

    rellenar('Valida123');
    component.submit();
    fixture.detectChanges();

    expect(component.failure()).toBe('expired');
    expect(fixture.nativeElement.textContent).toContain('Este enlace ha caducado.');
    expect(fixture.nativeElement.textContent).toContain('Pedir un enlace nuevo');
  });

  it('un fallo de conexión deja el formulario para reintentar', () => {
    crear('t'.repeat(43));
    spyOn(authService, 'resetPassword').and.returnValue(throwError(() => ({ status: 0 })));

    rellenar('Valida123');
    component.submit();

    expect(component.failure()).toBeNull();
    expect(component.error()).toContain('conexión');
  });
});
