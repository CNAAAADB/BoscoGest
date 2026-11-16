/** Spanish DNI and NIE checksum validation.
 * Checks the printed format and control letter, not the holder's identity.
 * X/Y/Z NIE prefixes correspond to 0/1/2 for the modulo-23 calculation.
 */
const CONTROL_LETTERS = 'TRWAGMYFPDXBNJZSQVHLCKE';

export function isValidSpanishDniOrNie(value: string): boolean {
  const document = value.toUpperCase().replace(/[\s-]/g, '');
  if (/^[0-9]{8}[A-Z]$/.test(document)) {
    const number = Number(document.slice(0, 8));
    return CONTROL_LETTERS[number % 23] === document[8];
  }
  if (/^[XYZ][0-9]{7}[A-Z]$/.test(document)) {
    const prefix = String('XYZ'.indexOf(document[0]));
    const number = Number(prefix + document.slice(1, 8));
    return CONTROL_LETTERS[number % 23] === document[8];
  }
  return false;
}
