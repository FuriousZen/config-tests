import { NewTaskInput } from '../types';

export interface ValidationResult {
  valid: boolean;
  errors: string[];
}

export const MAX_TITLE_LENGTH = 80;

export function validateTask(input: NewTaskInput): ValidationResult {
  const errors: string[] = [];
  if (!input.title || input.title.trim().length === 0) {
    errors.push('Title is required');
  }
  if (input.title && input.title.length > MAX_TITLE_LENGTH) {
    errors.push(`Title must be at most ${MAX_TITLE_LENGTH} characters`);
  }
  return { valid: errors.length === 0, errors };
}
