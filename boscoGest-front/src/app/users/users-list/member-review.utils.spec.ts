import { UserResponse } from '../../models/user.model';
import { memberReviewReasons } from './member-review.utils';

const complete: UserResponse = {
  id: 1, name: 'María', surname: 'López', email: 'maria@correo.es',
  phone: '612345678', dni: '12345678Z', birthdate: '1965-03-21',
  photo: null, job_position: null, is_active: true,
  must_change_password: false, created_at: '2026-01-01',
  iban: null, address: null, size: null, hobbies: null,
};

describe('Aviso de datos de socios', () => {
  const fullPermissions = { canReadContact: true, canReadSensitive: true };

  it('no muestra alerta para un socio completo', () => {
    expect(memberReviewReasons(complete, fullPermissions)).toEqual([]);
  });

  it('marca los campos de contacto e identificación sin completar', () => {
    const user = { ...complete, email: null, phone: null, dni: null };
    const reasons = memberReviewReasons(user, fullPermissions);
    expect(reasons).toContain('Falta el correo electrónico');
    expect(reasons).toContain('Falta el teléfono');
    expect(reasons).toContain('Falta el DNI');
  });

  it('reconoce marcadores de pruebas sin afirmar fraude', () => {
    const user = {
      ...complete,
      name: 'Prueba',
      email: 'test@example.com',
      phone: '666666666',
      dni: '00000000A',
      birthdate: '1900-01-01',
    };
    const reasons = memberReviewReasons(user, fullPermissions);
    expect(reasons).toContain('Nombre aparentemente de prueba');
    expect(reasons).toContain('Correo electrónico aparentemente de prueba');
    expect(reasons).toContain('Teléfono aparentemente de prueba');
    expect(reasons).toContain('DNI aparentemente de prueba');
    expect(reasons).toContain('Fecha de nacimiento posiblemente provisional');
  });

  it('no confunde campos ocultos por privacidad con campos incompletos', () => {
    const redacted = { ...complete, email: null, phone: null, dni: null, birthdate: null };
    expect(memberReviewReasons(redacted, {
      canReadContact: false,
      canReadSensitive: false,
    })).toEqual([]);
  });

  it('omite campos personales no obligatorios como dirección, IBAN o fotografía', () => {
    expect(memberReviewReasons(complete, fullPermissions)).toEqual([]);
  });

  it('no etiqueta como ficticios nombres reales que contienen prueba o test', () => {
    const user = { ...complete, name: 'Testa', surname: 'Del Prado' };
    expect(memberReviewReasons(user, fullPermissions)).toEqual([]);
  });
});
