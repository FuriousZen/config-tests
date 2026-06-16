import { describe, expect, it } from 'vitest';
import { formatRelativeDate } from '../../app/utils/date';

describe('formatRelativeDate', () => {
  const from = 1_000_000_000_000;

  it('returns "just now" for recent timestamps', () => {
    expect(formatRelativeDate(from - 5_000, from)).toBe('just now');
  });

  it('formats minutes and hours', () => {
    expect(formatRelativeDate(from - 5 * 60_000, from)).toBe('5m ago');
    expect(formatRelativeDate(from - 3 * 3_600_000, from)).toBe('3h ago');
  });

  it('formats days', () => {
    expect(formatRelativeDate(from - 2 * 86_400_000, from)).toBe('2d ago');
  });
});
