import { User } from '../types';
import { apiList, apiPut } from './client';

const COLLECTION = 'users';

export function fetchUsers(): Promise<User[]> {
  return apiList<User>(COLLECTION);
}

export function seedUser(user: User): Promise<User> {
  return apiPut(COLLECTION, user);
}
