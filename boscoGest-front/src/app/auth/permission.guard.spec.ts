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
import { provideAppTesting } from '../testing/test-providers';

/**
 * permissionGuard no es un CanActivateFn: es una factoría que devuelve uno a
 * partir de (resource, action). El stub que generaba el CLI lo invocaba como
 * si fuera el guard en sí, y por eso no compilaba — y con él, ninguna prueba
 * de la suite.
 */
describe('permissionGuard', () => {
  let authService: AuthService;
  let router: Router;

  function conMembresias(memberships: unknown[]) {
    (authService as unknown as { allMemberships: { set: (v: unknown) => void } })
      .allMemberships.set(memberships);
  }

  function membresia(permisos: [string, string][], nivel = 4, activa = true) {
    return {
      entity_id: nivel,
      entity: { id: nivel, level: nivel },
      is_active: activa,
      role: { permissions: permisos.map(([resource, action]) => ({ resource, action })) },
    };
  }

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideAppTesting(), provideRouter([])] });
    authService = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    spyOn(authService, 'isLoggedIn').and.returnValue(true);
    spyOn(authService, 'checkAuth').and.returnValue(of(true));
  });

  /** Ejecuta el guard dentro de un contexto de inyección, como hace el router. */
  function runGuard(resource = 'users', action = 'list', scope: 'any' | 'root' = 'any') {
    const guard = permissionGuard(resource, action, scope);
    return TestBed.runInInjectionContext(() =>
      guard({} as ActivatedRouteSnapshot, {} as RouterStateSnapshot),
    ) as Observable<boolean | UrlTree> | UrlTree;
  }

  function resultado(r: Observable<boolean | UrlTree> | UrlTree, done: (v: string | boolean) => void) {
    if (r instanceof UrlTree) return done(router.serializeUrl(r));
    r.subscribe((v) => done(v instanceof UrlTree ? router.serializeUrl(v) : v));
  }

  it('redirige al login cuando no hay sesión', () => {
    (authService.isLoggedIn as jasmine.Spy).and.returnValue(false);

    const r = runGuard() as UrlTree;

    expect(router.serializeUrl(r)).toBe('/login');
    expect(authService.checkAuth).not.toHaveBeenCalled();
  });

  it('deja pasar a quien tiene el permiso', (done) => {
    conMembresias([membresia([['roles', 'manage']])]);

    resultado(runGuard('roles', 'manage'), (v) => { expect(v).toBeTrue(); done(); });
  });

  it('redirige al dashboard a quien no lo tiene', (done) => {
    // Antes pasaba: el backend responde siempre 200 y cualquier 200 era un sí.
    conMembresias([membresia([['users', 'read'], ['users', 'list']])]);

    resultado(runGuard('users', 'manage'), (v) => { expect(v).toBe('/dashboard'); done(); });
  });

  it('cuenta manage_all como cualquier acción de su recurso', (done) => {
    conMembresias([membresia([['users', 'manage_all']])]);

    resultado(runGuard('users', 'update'), (v) => { expect(v).toBeTrue(); done(); });
  });

  it('ignora las membresías inactivas', (done) => {
    conMembresias([membresia([['users', 'manage']], 4, false)]);

    resultado(runGuard('users', 'manage'), (v) => { expect(v).toBe('/dashboard'); done(); });
  });

  it('con scope root exige el permiso en la raíz', (done) => {
    conMembresias([membresia([['fees', 'maintenance']], 4)]);

    resultado(runGuard('fees', 'maintenance', 'root'), (v) => {
      expect(v).toBe('/dashboard');
      conMembresias([membresia([['fees', 'maintenance']], 1)]);
      resultado(runGuard('fees', 'maintenance', 'root'), (w) => { expect(w).toBeTrue(); done(); });
    });
  });

  it('espera a la sesión: sin ella, al login', (done) => {
    (authService.checkAuth as jasmine.Spy).and.returnValue(of(false));

    resultado(runGuard(), (v) => { expect(v).toBe('/login'); done(); });
  });

  it('un error al cargar la sesión no deja la navegación colgada', (done) => {
    (authService.checkAuth as jasmine.Spy).and.returnValue(throwError(() => new Error('network')));

    resultado(runGuard(), (v) => { expect(v).toBe('/dashboard'); done(); });
  });
});
