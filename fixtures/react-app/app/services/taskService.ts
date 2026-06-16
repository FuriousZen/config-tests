import * as taskApi from '../api/tasks';
import { NewTaskInput, Task, TaskStatus } from '../types';
import { validateTask } from '../utils/validation';

export class ValidationError extends Error {
  constructor(public readonly errors: string[]) {
    super(errors.join(', '));
    this.name = 'ValidationError';
  }
}

export function getTasks(): Promise<Task[]> {
  return taskApi.fetchTasks();
}

export async function addTask(input: NewTaskInput): Promise<Task> {
  const result = validateTask(input);
  if (!result.valid) {
    throw new ValidationError(result.errors);
  }
  return taskApi.createTask(input);
}

export function moveTask(task: Task, status: TaskStatus): Promise<Task> {
  return taskApi.saveTask({ ...task, status });
}

export function removeTask(id: string): Promise<boolean> {
  return taskApi.deleteTask(id);
}
