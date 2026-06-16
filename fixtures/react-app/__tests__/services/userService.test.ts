import { describe, expect, it } from 'vitest';
import { findAssignee } from '../../app/services/userService';
import { User } from '../../app/types';

const users: User[] = [
  { id: 'u1', name: 'Ada Lovelace', email: 'ada@example.com', avatarColor: '#abc' },
  { id: 'u2', name: 'Alan Turing', email: 'alan@example.com', avatarColor: '#def' },
];

describe('findAssignee', () => {
  it('returns null for a null id', () => {
    expect(findAssignee(users, null)).toBeNull();
  });

  it('finds the matching user', () => {
    expect(findAssignee(users, 'u2')?.name).toBe('Alan Turing');
  });

  it('returns null when no user matches', () => {
    expect(findAssignee(users, 'nope')).toBeNull();
  });
});
