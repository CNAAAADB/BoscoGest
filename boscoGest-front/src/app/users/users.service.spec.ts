import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { UsersService } from './users.service';
import { provideAppTesting } from '../testing/test-providers';
import { environment } from '../../environments/environment';

describe('UsersService', () => {
  let service: UsersService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideAppTesting()],
    });
    service = TestBed.inject(UsersService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('deleteMyAccount', () => {
    it('envía DELETE a /users/me con la contraseña en el cuerpo', () => {
      let response: { message: string } | undefined;

      service.deleteMyAccount('Micontraseña1').subscribe((r) => (response = r));

      const req = httpMock.expectOne(`${environment.apiUrl}/users/me`);
      expect(req.request.method).toBe('DELETE');
      // El backend pide la contraseña en el cuerpo del DELETE; HttpClient solo
      // la envía si se pasa por la opción `body`, y es fácil perderla al
      // refactorizar sin que nada avise.
      expect(req.request.body).toEqual({ password: 'Micontraseña1' });

      req.flush({ message: 'Tu cuenta ha sido eliminada' });
      expect(response?.message).toBe('Tu cuenta ha sido eliminada');
    });

    it('no toca la ruta de borrado de otros usuarios', () => {
      service.deleteMyAccount('x').subscribe();

      // /users/me y /users/{id} son endpoints distintos y con permisos
      // distintos: confundirlos borraría la cuenta equivocada.
      httpMock.expectNone(`${environment.apiUrl}/users/undefined`);
      httpMock.expectOne(`${environment.apiUrl}/users/me`).flush({ message: 'ok' });
    });
  });
});
