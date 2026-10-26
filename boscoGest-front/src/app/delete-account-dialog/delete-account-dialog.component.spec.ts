import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialogRef } from '@angular/material/dialog';
import { of, throwError } from 'rxjs';

import { DeleteAccountDialogComponent } from './delete-account-dialog.component';
import { UsersService } from '../users/users.service';
import { provideAppTesting } from '../testing/test-providers';

/**
 * El borrado de cuenta es irreversible y es, además, el requisito que Google
 * Play comprueba antes de aprobar la ficha. Lo que se prueba aquí es que no se
 * puede disparar por accidente y que un fallo del servidor se explica en vez
 * de dejar el diálogo mudo.
 */
describe('DeleteAccountDialogComponent', () => {
  let component: DeleteAccountDialogComponent;
  let fixture: ComponentFixture<DeleteAccountDialogComponent>;
  let usersService: jasmine.SpyObj<UsersService>;
  let dialogRef: jasmine.SpyObj<MatDialogRef<DeleteAccountDialogComponent>>;

  beforeEach(async () => {
    usersService = jasmine.createSpyObj<UsersService>('UsersService', ['deleteMyAccount']);
    dialogRef = jasmine.createSpyObj<MatDialogRef<DeleteAccountDialogComponent>>(
      'MatDialogRef',
      ['close'],
    );

    await TestBed.configureTestingModule({
      imports: [DeleteAccountDialogComponent],
      providers: [
        provideAppTesting(),
        { provide: UsersService, useValue: usersService },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeleteAccountDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  /** Rellena el formulario como lo haría alguien decidido a borrar su cuenta. */
  function fillForm(password = 'Micontraseña1', understood = true): void {
    component.deleteForm.setValue({ password, understood });
  }

  function errorOf(status: number, detail?: string): HttpErrorResponse {
    return new HttpErrorResponse({ status, error: detail ? { detail } : null });
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('arranca con el formulario inválido', () => {
    // El botón de borrar está enlazado a deleteForm.invalid, así que abrir el
    // diálogo y pulsar no puede bastar.
    expect(component.deleteForm.invalid).toBeTrue();
  });

  it('exige marcar la casilla de confirmación además de la contraseña', () => {
    fillForm('Micontraseña1', false);

    expect(component.deleteForm.invalid).toBeTrue();

    component.onSubmit();
    expect(usersService.deleteMyAccount).not.toHaveBeenCalled();
  });

  it('exige la contraseña además de la casilla', () => {
    fillForm('', true);

    component.onSubmit();
    expect(usersService.deleteMyAccount).not.toHaveBeenCalled();
  });

  it('envía la contraseña y cierra con true al borrar', () => {
    usersService.deleteMyAccount.and.returnValue(of({ message: 'Cuenta eliminada' }));
    fillForm();

    component.onSubmit();

    expect(usersService.deleteMyAccount).toHaveBeenCalledWith('Micontraseña1');
    // true es lo que hace que quien abrió el diálogo cierre la sesión local.
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it('no envía dos veces si se pulsa mientras está en curso', () => {
    usersService.deleteMyAccount.and.returnValue(of({ message: 'ok' }));
    fillForm();

    component.onSubmit();
    component.onSubmit();

    expect(usersService.deleteMyAccount).toHaveBeenCalledTimes(1);
  });

  it('avisa de que la contraseña es incorrecta y mantiene el diálogo abierto', () => {
    usersService.deleteMyAccount.and.returnValue(throwError(() => errorOf(401)));
    fillForm('equivocada');

    component.onSubmit();

    expect(component.errorMessage()).toBe('La contraseña no es correcta.');
    expect(dialogRef.close).not.toHaveBeenCalled();
    // Y se puede reintentar: el botón vuelve a estar disponible.
    expect(component.isSubmitting()).toBeFalse();
  });

  it('muestra el motivo del servidor cuando es el último administrador', () => {
    const detail =
      'Eres la única cuenta con administración total. Traspasa ese rol a otra ' +
      'persona antes de eliminar la tuya.';
    usersService.deleteMyAccount.and.returnValue(throwError(() => errorOf(409, detail)));
    fillForm();

    component.onSubmit();

    // El backend explica qué hacer; repetirlo aquí con un texto genérico
    // dejaría a esa persona sin saber por dónde salir.
    expect(component.errorMessage()).toBe(detail);
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('da un mensaje genérico ante un error sin detalle', () => {
    usersService.deleteMyAccount.and.returnValue(throwError(() => errorOf(500)));
    fillForm();

    component.onSubmit();

    expect(component.errorMessage()).toBe(
      'No se ha podido eliminar la cuenta. Inténtalo de nuevo más tarde.',
    );
  });

  it('cierra con false al cancelar, sin llamar al backend', () => {
    component.onCancel();

    expect(dialogRef.close).toHaveBeenCalledWith(false);
    expect(usersService.deleteMyAccount).not.toHaveBeenCalled();
  });
});
