import { UserResponse } from '../../models/user.model';
import { isValidSpanishDniOrNie } from './spanish-id.utils';

/** Field visibility matters: a privacy-redacted null is NOT missing data. */
export interface MemberReviewPermissions {
  canReadContact: boolean;
  canReadSensitive: boolean;
}

const hasValue = (value: string | null | undefined): boolean =>
  typeof value === 'string' && value.trim().length > 0;

const normalized = (value: string | null | undefined): string =>
  (value ?? '').trim().toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g, '');

const suspiciousName = (value: string | null | undefined): boolean =>
  /^(?:test|testing|prueba|demo|ejemplo|ficticio|fake|xxx|aaaa+|nn+)$/i.test(normalized(value));

const suspiciousEmail = (value: string | null | undefined): boolean => {
  if (!hasValue(value)) return false;
  const email = normalized(value);
  return /@(?:example\.(?:com|org|net)|example|test|invalid|localhost)(?:$|\.)/.test(email) ||
    /^(?:test|prueba|demo|ficticio|fake)(?:[0-9]*)@/.test(email);
};

const suspiciousPhone = (value: string | null | undefined): boolean => {
  if (!hasValue(value)) return false;
  const digits = value!.replace(/\D/g, '');
  return digits.length >= 9 && (/^(\d)\1+$/.test(digits) || /^(?:123456789|987654321|000000000)$/.test(digits));
};

const suspiciousDni = (value: string | null | undefined): boolean => {
  if (!hasValue(value)) return false;
  const dni = normalized(value).replace(/[\s-]/g, '').toUpperCase();
  return /^(?:0{8}[A-Z]?|1{8}[A-Z]?|X{8,9}|12345678[A-Z]?|99999999[A-Z]?)$/.test(dni);
};

/**
 * Display-only suggestions, never a claim of fraud or an account restriction.
 * We exclude optional fields like photo, hobbies, IBAN and address: their
 * absence is not an incomplete member record.
 */
export function memberReviewReasons(
  user: UserResponse,
  permissions: MemberReviewPermissions,
): string[] {
  const reasons: string[] = [];

  if (!hasValue(user.name)) reasons.push('Falta el nombre');
  else if (suspiciousName(user.name)) reasons.push('Nombre aparentemente de prueba');

  if (!hasValue(user.surname)) reasons.push('Faltan los apellidos');
  else if (suspiciousName(user.surname)) reasons.push('Apellidos aparentemente de prueba');

  if (permissions.canReadContact) {
    if (!hasValue(user.email)) reasons.push('Falta el correo electrónico');
    else if (suspiciousEmail(user.email)) reasons.push('Correo electrónico aparentemente de prueba');

    if (!hasValue(user.phone)) reasons.push('Falta el teléfono');
    else if (suspiciousPhone(user.phone)) reasons.push('Teléfono aparentemente de prueba');
  }

  if (permissions.canReadSensitive) {
    if (!hasValue(user.dni)) reasons.push('Falta el DNI');
    else if (suspiciousDni(user.dni)) reasons.push('DNI aparentemente de prueba');
    else if (!isValidSpanishDniOrNie(user.dni!)) reasons.push('DNI/NIE inválido: comprueba el formato y la letra de control');

    if (!hasValue(user.birthdate)) reasons.push('Falta la fecha de nacimiento');
    else if (/^(?:1900|1901|1970)-01-01$/.test(user.birthdate!))
      reasons.push('Fecha de nacimiento posiblemente provisional');
  }

  return reasons;
}
