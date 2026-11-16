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

  it('combina asociación con búsqueda y pendientes en usuarios gestionados', () => {
    service.getManagedUsers(25, 25, 'García', true, 42).subscribe();
    const request = httpMock.expectOne(req =>
      req.url === `${environment.apiUrl}/users/managed`
    );
    expect(request.request.params.get('entity_id')).toBe('42');
    expect(request.request.params.get('review_only')).toBe('true');
    expect(request.request.params.get('search')).toBe('García');
    expect(request.request.params.get('skip')).toBe('25');
    request.flush({ items: [], total: 0, skip: 25, limit: 25 });
  });

  it('filtra por asociación en el listado general sin exigir pendientes', () => {
    service.getUsers(0, 25, 'Ana', 99).subscribe();
    const request = httpMock.expectOne(req =>
      req.url === `${environment.apiUrl}/users`
    );
    expect(request.request.params.get('entity_id')).toBe('99');
    expect(request.request.params.has('review_only')).toBeFalse();
    request.flush({ items: [], total: 0, skip: 0, limit: 25 });
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
