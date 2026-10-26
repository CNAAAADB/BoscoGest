import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { of } from 'rxjs';

import { MyProfileComponent } from './my-profile.component';
import { DeleteAccountDialogComponent } from '../delete-account-dialog/delete-account-dialog.component';
import { AuthService } from '../auth/auth.service';
import { provideAppTesting } from '../testing/test-providers';

describe('MyProfileComponent', () => {
  let component: MyProfileComponent;
  let fixture: ComponentFixture<MyProfileComponent>;
  let dialog: jasmine.SpyObj<MatDialog>;
  let authService: jasmine.SpyObj<AuthService>;

  /** Hace que el siguiente dialog.open() se cierre con el resultado dado. */
  function dialogClosesWith(result: unknown): void {
    dialog.open.and.returnValue({
      afterClosed: () => of(result),
    } as MatDialogRef<unknown>);
  }

  beforeEach(async () => {
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    authService = jasmine.createSpyObj<AuthService>('AuthService', [
      'getCurrentUser',
      'getCurrentMembership',
      'endSession',
    ]);
    authService.getCurrentUser.and.returnValue(null);
    authService.getCurrentMembership.and.returnValue(null);
    dialogClosesWith(false);

    await TestBed.configureTestingModule({
      imports: [MyProfileComponent],
      providers: [
        provideAppTesting(),
        { provide: AuthService, useValue: authService },
      ],
    })
      // MatDialog no basta con declararlo en providers: el componente importa
      // MatDialogModule, que vuelve a proveerlo y gana sobre el del TestBed.
      // overrideProvider sustituye también esa declaración.
      .overrideProvider(MatDialog, { useValue: dialog })
      .compileComponents();

    fixture = TestBed.createComponent(MyProfileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('borrado de cuenta', () => {
    it('abre el diálogo de borrado', () => {
      component.openDeleteAccountDialog();

      expect(dialog.open).toHaveBeenCalledWith(
        DeleteAccountDialogComponent,
        jasmine.objectContaining({ disableClose: true }),
      );
    });

    it('cierra la sesión local cuando la cuenta se ha borrado', () => {
      dialogClosesWith(true);

      component.openDeleteAccountDialog();

      // El token ya está revocado en el servidor: pedir un logout devolvería
      // 401, así que aquí solo se limpia la sesión y se vuelve al login.
      expect(authService.endSession).toHaveBeenCalled();
    });

    it('no cierra la sesión si se cancela el diálogo', () => {
      dialogClosesWith(false);

      component.openDeleteAccountDialog();

      expect(authService.endSession).not.toHaveBeenCalled();
    });
  });
});
