import { useEffect, useState } from 'react';
import { getUsers } from '../services/userService';
import { User } from '../types';

export function useUsers(): User[] {
  const [users, setUsers] = useState<User[]>([]);
  useEffect(() => {
    void getUsers().then(setUsers);
  }, []);
  return users;
}
