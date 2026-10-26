import { activityNotFinished, activityStatus, formatActivityDates } from './activity-dates';

describe('activity-dates', () => {
  const now = new Date(2026, 10, 14, 12, 0); // 14 nov 2026, 12:00
  const at = (d: number, h: number, m = 0) => new Date(2026, 10, d, h, m).toISOString();

  describe('activityStatus', () => {
    it('is upcoming before it starts', () => {
      expect(activityStatus({ date: at(15, 10), end_date: at(17, 18) }, now)).toBe('upcoming');
    });

    it('is ongoing between start and end: a camp that began yesterday', () => {
      expect(activityStatus({ date: at(13, 17), end_date: at(15, 18) }, now)).toBe('ongoing');
    });

    it('is past once it has ended', () => {
      expect(activityStatus({ date: at(10, 10), end_date: at(12, 18) }, now)).toBe('past');
    });

    it('without an end, is over as soon as it starts, as before', () => {
      expect(activityStatus({ date: at(14, 11), end_date: null }, now)).toBe('past');
      expect(activityStatus({ date: at(14, 13) }, now)).toBe('upcoming');
    });
  });

  it('keeps ongoing activities among the ones not finished', () => {
    expect(activityNotFinished({ date: at(13, 17), end_date: at(15, 18) }, now)).toBeTrue();
    expect(activityNotFinished({ date: at(13, 17), end_date: at(13, 20) }, now)).toBeFalse();
  });

  describe('formatActivityDates', () => {
    it('shows only the start when there is no end', () => {
      const text = formatActivityDates({ date: at(13, 17), end_date: null });
      expect(text).toContain('13');
      expect(text).not.toContain('–');
    });

    it('shows only the closing time when it ends the same day', () => {
      const text = formatActivityDates({ date: at(13, 10), end_date: at(13, 14) });
      expect(text).toMatch(/10:00 – 14:00$/);
    });

    it('shows both days when it spans several', () => {
      const text = formatActivityDates({ date: at(13, 17), end_date: at(15, 18) });
      expect(text).toContain('13');
      expect(text).toContain('15');
      expect(text).toMatch(/18:00$/);
    });
  });
});
