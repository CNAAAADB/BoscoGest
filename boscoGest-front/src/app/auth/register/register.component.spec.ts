import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';

import { RegisterComponent } from './register.component';
import { MembershipRequestService } from '../../membership-requests/membership-request.service';
import { provideAppTesting } from '../../testing/test-providers';

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let register: jasmine.Spy;

  beforeEach(() => {
    register = jasmine.createSpy('register');
    TestBed.configureTestingModule({
      imports: [RegisterComponent],
      providers: [
        provideAppTesting(),
        {
          provide: MembershipRequestService,
          useValue: { register, getPublicEntities: () => of([]) },
        },
      ],
    });
    component = TestBed.createComponent(RegisterComponent).componentInstance;
    component.selectedEntityId.set(1);
    component.currentStep.set(1);
  });

  it('vuelve al primer paso si el DNI ya está registrado, con el motivo', () => {
    const detail = 'Ya existe una cuenta con ese DNI. Si ya te habían dado de alta, inicia sesión en lugar de registrarte.';
    register.and.returnValue(throwError(() => new HttpErrorResponse({ status: 409, error: { detail } })));

    component.submit();

    expect(component.currentStep()).toBe(0);
    expect(component.errorMessage()).toBe(detail);
  });

  it('se queda en el paso en que está si el error es de otro tipo', () => {
    register.and.returnValue(throwError(() => new HttpErrorResponse({ status: 500, error: {} })));

    component.submit();

    expect(component.currentStep()).toBe(1);
    expect(component.errorMessage()).toBe('Error al enviar la solicitud');
  });
});
