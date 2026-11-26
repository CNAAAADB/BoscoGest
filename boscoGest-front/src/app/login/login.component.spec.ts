import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LoginComponent } from './login.component';
import { provideAppTesting } from '../testing/test-providers';

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [provideAppTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('shows and hides the password without changing its value or submitting the form', async () => {
    const submit = spyOn(component, 'onLogin');
    const input: HTMLInputElement = fixture.nativeElement.querySelector('input[name="password"]');
    const button: HTMLButtonElement = fixture.nativeElement.querySelector('button[aria-label="Mostrar contraseña"]');

    component.password.set('Prueba123');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(input.type).toBe('password');
    expect(input.value).toBe('Prueba123');
    expect(button.type).toBe('button');

    button.click();
    fixture.detectChanges();
    expect(input.type).toBe('text');
    expect(button.getAttribute('aria-label')).toBe('Ocultar contraseña');
    expect(input.value).toBe('Prueba123');

    button.click();
    fixture.detectChanges();
    expect(input.type).toBe('password');
    expect(button.getAttribute('aria-label')).toBe('Mostrar contraseña');
    expect(component.password()).toBe('Prueba123');
    expect(submit).not.toHaveBeenCalled();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
