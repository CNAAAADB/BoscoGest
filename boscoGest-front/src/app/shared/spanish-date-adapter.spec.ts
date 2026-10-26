import { TestBed } from '@angular/core/testing';
import { DateAdapter } from '@angular/material/core';
import { provideAppTesting } from '../testing/test-providers';

describe('SpanishDateAdapter', () => {
  let adapter: DateAdapter<Date>;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideAppTesting() });
    adapter = TestBed.inject(DateAdapter);
  });

  const ymd = (d: Date | null) =>
    d && adapter.isValid(d) ? [d.getFullYear(), d.getMonth() + 1, d.getDate()] : null;

  it('reads day before month, as it is written in Spain', () => {
    expect(ymd(adapter.parse('05/11/2026', null))).toEqual([2026, 11, 5]);
    expect(ymd(adapter.parse('13/11/2026', null))).toEqual([2026, 11, 13]);
    expect(ymd(adapter.parse('5-3-1948', null))).toEqual([1948, 3, 5]);
  });

  it('reads back what it displays', () => {
    const date = new Date(1950, 0, 15);
    const shown = adapter.format(date, { year: 'numeric', month: 'numeric', day: 'numeric' });
    expect(ymd(adapter.parse(shown, null))).toEqual([1950, 1, 15]);
  });

  it('reads ISO dates as that local day, not the day before', () => {
    expect(ymd(adapter.parse('2026-11-13', null))).toEqual([2026, 11, 13]);
  });

  it('rejects dates that do not exist and two-digit years instead of guessing', () => {
    expect(ymd(adapter.parse('31/02/1950', null))).toBeNull();
    expect(ymd(adapter.parse('01/13/1950', null))).toBeNull();
    expect(ymd(adapter.parse('15/01/50', null))).toBeNull();
  });

  it('treats an empty field as no date', () => {
    expect(adapter.parse('', null)).toBeNull();
  });
});
