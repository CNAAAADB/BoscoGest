import { Injectable } from '@angular/core';
import { NativeDateAdapter } from '@angular/material/core';

const DAY_FIRST = /^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$/;
const ISO_DATE = /^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$/;

/**
 * Reads a typed date the way it is written in Spain: day, month, year.
 *
 * NativeDateAdapter shows dates in the configured locale (13/11/2026) but reads
 * what is typed with Date.parse, which assumes the American order. So the same
 * field printed 13/11/2026 and rejected it when typed back, and 05/11/2026
 * turned into the 11th of May without any warning — for a birthdate, a wrong
 * date that nobody notices.
 *
 * The year must have four digits; with two there is no telling the century.
 */
@Injectable()
export class SpanishDateAdapter extends NativeDateAdapter {
  override parse(value: unknown, parseFormat?: unknown): Date | null {
    if (typeof value === 'string') {
      const dayFirst = DAY_FIRST.exec(value);
      if (dayFirst) {
        return this.build(+dayFirst[3], +dayFirst[2], +dayFirst[1]);
      }
      const iso = ISO_DATE.exec(value);
      if (iso) {
        // Date.parse would read it as UTC midnight, which west of Greenwich
        // is still the day before.
        return this.build(+iso[1], +iso[2], +iso[3]);
      }
      if (/^\s*\d/.test(value)) {
        // Digits in any other shape (15/01/50, 2026/11/13…): ambiguous, so
        // rejected rather than guessed.
        return value.trim() ? this.invalid() : null;
      }
    }
    return super.parse(value, parseFormat);
  }

  /** The date, or an invalid one if it does not exist (31/02, month 13…). */
  private build(year: number, month: number, day: number): Date {
    const date = new Date(year, month - 1, day);
    const exists = date.getFullYear() === year
      && date.getMonth() === month - 1
      && date.getDate() === day;
    return exists ? date : this.invalid();
  }
}
