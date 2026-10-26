import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  provideRouter,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';
import { Observable, of, throwError } from 'rxjs';

import { permissionGuard } from './permission.guard';
import { AuthService } from './auth.service';

/**
 * permissionGuard no es un CanActivateFn: es una factoría que devuelve uno a
 * partir de (resource, action). El stub que generaba el CLI lo invocaba como
 * si fuera el guard en sí, y por eso no compilaba — y con él, ninguna prueba
 * de la suite.
 */
describe('permissionGuard', () => {
  let authService: jasmine.SpyObj<AuthService>;
  let router: Router;

  beforeEach(() => {
    authService = jasmine.createSpyObj<AuthService>('AuthService', [
      'isLoggedIn',
      'checkPermission',
    ]);

    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: authService }],
    });

    router = TestBed.inject(Router);
  });

  /** Ejecuta el guard dentro de un contexto de inyección, como hace el router. */
  function runGuard(resource = 'users', action = 'list') {
    const guard = permissionGuard(resource, action);
    return TestBed.runInInjectionContext(() =>
      guard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    );
  }

  it('redirige al login cuando no hay sesión', () => {
    authService.isLoggedIn.and.returnValue(false);

    const result = runGuard();

    expect(router.serializeUrl(result as UrlTree)).toBe('/login');
    // Sin sesión no tiene sentido preguntar al backend: la llamada daría 401.
    expect(authService.checkPermission).not.toHaveBeenCalled();
  });

  it('deja pasar cuando el backend concede el permiso', (done) => {
    authService.isLoggedIn.and.returnValue(true);
    authService.checkPermission.and.returnValue(of(true));

    (runGuard('roles', 'manage') as Observable<boolean | UrlTree>).subscribe((result) => {
      expect(result).toBeTrue();
      expect(authService.checkPermission).toHaveBeenCalledWith('roles', 'manage');
      done();
    });
  });

  it('redirige al dashboard cuando el permiso se deniega', (done) => {
    authService.isLoggedIn.and.returnValue(true);
    authService.checkPermission.and.returnValue(of(false));

    (runGuard() as Observable<boolean | UrlTree>).subscribe((result) => {
      expect(router.serializeUrl(result as UrlTree)).toBe('/dashboard');
      done();
    });
  });

  it('redirige al dashboard cuando la comprobación falla', (done) => {
    authService.isLoggedIn.and.returnValue(true);
    authService.checkPermission.and.returnValue(throwError(() => new Error('network')));

    // Un error de red no debe dejar la navegación colgada ni propagar la
    // excepción al router: cae al dashboard, como una denegación.
    (runGuard() as Observable<boolean | UrlTree>).subscribe((result) => {
      expect(router.serializeUrl(result as UrlTree)).toBe('/dashboard');
      done();
    });
  });
});
