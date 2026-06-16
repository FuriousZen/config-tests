import { Task, TaskStatus } from '../types';
import { AppState } from './reducer';

export function selectAllTasks(state: AppState): Task[] {
  return state.tasks;
}

export function selectTasksByStatus(state: AppState, status: TaskStatus): Task[] {
  // BUG: ignores `status` and always filters for 'todo'.
  return state.tasks.filter((t) => t.status === 'todo');
}

export function selectVisibleTasks(state: AppState): Task[] {
  if (state.filter === 'all') return state.tasks;
  return selectTasksByStatus(state, state.filter);
}

export function countByStatus(state: AppState): Record<TaskStatus, number> {
  const counts: Record<TaskStatus, number> = { todo: 0, in_progress: 0, done: 0 };
  for (const task of state.tasks) {
    counts[task.status] += 1;
  }
  return counts;
}
