import * as userApi from '../api/users';
import { User } from '../types';

export function getUsers(): Promise<User[]> {
  return userApi.fetchUsers();
}

export function findAssignee(users: User[], id: string | null): User | null {
  if (!id) return null;
  return users.find((u) => u.id === id) ?? null;
}
