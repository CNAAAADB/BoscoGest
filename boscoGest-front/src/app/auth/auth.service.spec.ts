import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { provideAppTesting } from '../testing/test-providers';
import { environment } from '../../environments/environment';

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  const me = {
    id: 7, name: 'Clara', surname: 'Contreras', dni: '12345678A',
    birthdate: '1950-01-15', email: 'clara@ejemplo.com',
  };

  beforeEach(() => {
    localStorage.removeItem('authToken');
    TestBed.configureTestingModule({
      providers: [provideAppTesting()],
    });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    localStorage.removeItem('authToken');
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('la persona de la sesión', () => {
    beforeEach(() => localStorage.setItem('authToken', 'token'));

    it('existe aunque aún no tenga asociaciones (solicitud pendiente)', () => {
      let ok: boolean | undefined;
      service.checkAuth().subscribe((v) => (ok = v));

      http.expectOne(`${environment.apiUrl}/memberships`).flush([]);
      http.expectOne(`${environment.apiUrl}/users/me`).flush(me);

      expect(ok).toBeTrue();
      expect(service.hasMemberships()).toBeFalse();
      expect(service.getCurrentUser()?.name).toBe('Clara');
      expect(service.getCurrentUser()?.dni).toBe('12345678A');
    });

    it('sale de /users/me y no de la primera asociación', () => {
      service.checkAuth().subscribe();

      http.expectOne(`${environment.apiUrl}/memberships`).flush([
        { id: 1, entity_id: 3, user: { id: 7, name: 'Otro', surname: 'Nombre' }, role: null },
      ]);
      http.expectOne(`${environment.apiUrl}/users/me`).flush(me);

      expect(service.hasMemberships()).toBeTrue();
      expect(service.getCurrentUser()?.name).toBe('Clara');
    });
  });
});
