import React from 'react';
import { useUsers } from '../../hooks/useUsers';
import { findAssignee } from '../../services/userService';
import { Task } from '../../types';
import { formatRelativeDate } from '../../utils/date';
import { Avatar } from '../common/Avatar';
import { TaskBadge } from './TaskBadge';

export function TaskCard({ task }: { task: Task }) {
  const users = useUsers();
  const assignee = findAssignee(users, task.assigneeId);
  return (
    <div className="task-card">
      <header className="task-card-header">
        <h4>{task.title}</h4>
        <TaskBadge priority={task.priority} />
      </header>
      {task.description && <p className="task-card-body">{task.description}</p>}
      <footer className="task-card-footer">
        <Avatar user={assignee} />
        <time>{formatRelativeDate(task.updatedAt)}</time>
      </footer>
    </div>
  );
}
