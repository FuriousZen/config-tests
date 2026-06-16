import { describe, expect, it } from 'vitest';
import { MAX_TITLE_LENGTH, validateTask } from '../../app/utils/validation';

describe('validateTask', () => {
  it('accepts a valid title', () => {
    expect(validateTask({ title: 'Write docs' })).toEqual({ valid: true, errors: [] });
  });

  it('rejects an empty or whitespace title', () => {
    expect(validateTask({ title: '' }).valid).toBe(false);
    expect(validateTask({ title: '   ' }).errors).toContain('Title is required');
  });

  it('rejects a title over the max length', () => {
    const result = validateTask({ title: 'x'.repeat(MAX_TITLE_LENGTH + 1) });
    expect(result.valid).toBe(false);
  });
});
