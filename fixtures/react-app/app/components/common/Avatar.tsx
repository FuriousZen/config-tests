import React from 'react';
import { User } from '../../types';

export function Avatar({ user }: { user: User | null }) {
  if (!user) {
    return <span className="avatar avatar-empty">?</span>;
  }
  const initials = user.name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();
  return (
    <span className="avatar" style={{ background: user.avatarColor }} title={user.name}>
      {initials}
    </span>
  );
}
