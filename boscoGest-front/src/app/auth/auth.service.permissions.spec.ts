import { TestBed } from '@angular/core/testing';

import { AuthService } from './auth.service';
import { provideAppTesting } from '../testing/test-providers';

/**
 * `hasPermissionAtEntity` decide qué botones se enseñan para los permisos que
 * **no se heredan** — `memberships:*` entre ellos—, que solo valen en la
 * asociación donde se tienen. Equivocarse aquí significa enseñar acciones que
 * el servidor va a rechazar, o esconder las que sí se pueden hacer.
 */
describe('AuthService.hasPermissionAtEntity', () => {
  let service: AuthService;

  const CADIZ = 10;
  const SEVILLA = 20;

  function conMembresias(memberships: unknown[]) {
    // allMemberships es una señal privada; se alimenta por el método público
    // que usa el resto de la aplicación.
    (service as unknown as { allMemberships: { set: (v: unknown) => void } })
      .allMemberships.set(memberships);
  }

  function membresia(entityId: number, permisos: [string, string][], activa = true, nivel = 4) {
    return {
      entity_id: entityId,
      entity: { id: entityId, level: nivel },
      is_active: activa,
      role: {
        permissions: permisos.map(([resource, action]) => ({ resource, action })),
      },
    };
  }

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideAppTesting()] });
    service = TestBed.inject(AuthService);
  });

  it('concede el permiso en la asociación donde se tiene', () => {
    conMembresias([membresia(CADIZ, [['memberships', 'update']])]);

    expect(service.hasPermissionAtEntity(CADIZ, 'memberships', 'update')).toBeTrue();
  });

  it('NO lo concede en otra asociación', () => {
    conMembresias([membresia(CADIZ, [['memberships', 'update']])]);

    // Es el fallo que importa: memberships:update no se hereda ni se contagia,
    // así que ser admin en Cádiz no da derecho sobre Sevilla.
    expect(service.hasPermissionAtEntity(SEVILLA, 'memberships', 'update')).toBeFalse();
  });

  it('manage_all vale en su propia asociación', () => {
    conMembresias([membresia(CADIZ, [['memberships', 'manage_all']])]);

    expect(service.hasPermissionAtEntity(CADIZ, 'memberships', 'update')).toBeTrue();
  });

  it('manage_all de una asociación local no vale en otra', () => {
    // El backend dejó de aceptarlo fuera de su jerarquía.
    conMembresias([membresia(CADIZ, [['memberships', 'manage_all']])]);

    expect(service.hasPermissionAtEntity(SEVILLA, 'memberships', 'update')).toBeFalse();
  });

  it('manage_all desde la raíz vale en todas', () => {
    conMembresias([membresia(1, [['memberships', 'manage_all']], true, 1)]);

    expect(service.hasPermissionAtEntity(SEVILLA, 'memberships', 'update')).toBeTrue();
  });

  describe('hasRootPermission', () => {
    it('solo con el permiso en una membresía de la raíz', () => {
      conMembresias([membresia(CADIZ, [['consent', 'manage']])]);
      expect(service.hasRootPermission('consent', 'manage')).toBeFalse();

      conMembresias([membresia(1, [['consent', 'manage']], true, 1)]);
      expect(service.hasRootPermission('consent', 'manage')).toBeTrue();
    });

    it('ignora la membresía de la raíz si está inactiva', () => {
      conMembresias([membresia(1, [['fees', 'maintenance']], false, 1)]);

      expect(service.hasRootPermission('fees', 'maintenance')).toBeFalse();
    });
  });

  it('ignora las membresías inactivas', () => {
    conMembresias([membresia(CADIZ, [['memberships', 'update']], false)]);

    expect(service.hasPermissionAtEntity(CADIZ, 'memberships', 'update')).toBeFalse();
  });

  it('no confunde recursos ni acciones distintas', () => {
    conMembresias([membresia(CADIZ, [['memberships', 'read'], ['users', 'update']])]);

    expect(service.hasPermissionAtEntity(CADIZ, 'memberships', 'update')).toBeFalse();
  });

  it('sin membresías no concede nada', () => {
    conMembresias([]);

    expect(service.hasPermissionAtEntity(CADIZ, 'memberships', 'update')).toBeFalse();
  });

  it('un socio raso no puede cambiar roles', () => {
    conMembresias([membresia(CADIZ, [['memberships', 'read'], ['activities', 'read']])]);

    expect(service.hasPermissionAtEntity(CADIZ, 'memberships', 'update')).toBeFalse();
  });
});
