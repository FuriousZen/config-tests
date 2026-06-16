import { NewTaskInput, Task } from '../types';
import { now } from '../utils/date';
import { createId } from '../utils/id';
import { apiDelete, apiGet, apiList, apiPut } from './client';

const COLLECTION = 'tasks';

export function fetchTasks(): Promise<Task[]> {
  return apiList<Task>(COLLECTION);
}

export function fetchTask(id: string): Promise<Task | null> {
  return apiGet<Task>(COLLECTION, id);
}

export function createTask(input: NewTaskInput): Promise<Task> {
  const task: Task = {
    id: createId('task'),
    title: input.title,
    description: input.description ?? '',
    status: 'todo',
    priority: input.priority ?? 'medium',
    assigneeId: input.assigneeId ?? null,
    createdAt: now(),
    updatedAt: now(),
  };
  return apiPut(COLLECTION, task);
}

export function saveTask(task: Task): Promise<Task> {
  return apiPut(COLLECTION, { ...task, updatedAt: now() });
}

export function deleteTask(id: string): Promise<boolean> {
  return apiDelete(COLLECTION, id);
}
