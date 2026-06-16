import { beforeEach, describe, expect, it } from 'vitest';
import { createTask, deleteTask, fetchTasks, saveTask } from '../../app/api/tasks';

async function clear() {
  for (const task of await fetchTasks()) {
    await deleteTask(task.id);
  }
}

describe('api/tasks', () => {
  beforeEach(clear);

  it('createTask persists with defaults', async () => {
    const task = await createTask({ title: 'A' });
    expect(task.priority).toBe('medium');
    expect(await fetchTasks()).toHaveLength(1);
  });

  it('saveTask updates updatedAt and replaces the record', async () => {
    const task = await createTask({ title: 'A' });
    const saved = await saveTask({ ...task, status: 'done' });
    expect(saved.status).toBe('done');
    expect(saved.updatedAt).toBeGreaterThanOrEqual(task.updatedAt);
  });

  it('deleteTask removes the record', async () => {
    const task = await createTask({ title: 'A' });
    expect(await deleteTask(task.id)).toBe(true);
    expect(await fetchTasks()).toHaveLength(0);
  });
});
