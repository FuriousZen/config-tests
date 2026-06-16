import { TaskPriority, TaskStatus } from '../types';

export function formatStatus(status: TaskStatus): string {
  switch (status) {
    case 'todo':
      return 'To Do';
    case 'in_progress':
      return 'In Progress';
    case 'done':
      return 'Done';
  }
}

export function formatPriority(priority: TaskPriority): string {
  return priority.charAt(0).toUpperCase() + priority.slice(1);
}
