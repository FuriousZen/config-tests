import { Task, TaskStatus } from '../types';

export type Action =
  | { type: 'SET_TASKS'; tasks: Task[] }
  | { type: 'UPSERT_TASK'; task: Task }
  | { type: 'REMOVE_TASK'; id: string }
  | { type: 'SET_FILTER'; status: TaskStatus | 'all' };
