import React from 'react';
import { TaskPriority } from '../../types';
import { formatPriority } from '../../utils/format';

export function TaskBadge({ priority }: { priority: TaskPriority }) {
  return <span className={`badge badge-${priority}`}>{formatPriority(priority)}</span>;
}
