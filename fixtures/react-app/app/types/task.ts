export type TaskStatus = 'todo' | 'in_progress' | 'done';

export type TaskPriority = 'low' | 'medium' | 'high';

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  assigneeId: string | null;
  createdAt: number;
  updatedAt: number;
}

export interface NewTaskInput {
  title: string;
  description?: string;
  priority?: TaskPriority;
  assigneeId?: string | null;
}
