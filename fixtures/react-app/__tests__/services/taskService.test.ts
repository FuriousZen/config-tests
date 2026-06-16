import { beforeEach, describe, expect, it } from 'vitest';
import { addTask, getTasks, ValidationError } from '../../app/services/taskService';

describe('taskService', () => {
  beforeEach(async () => {
    // Clear any tasks left by other specs (in-memory backend is module state).
    for (const task of await getTasks()) {
      await import('../../app/api/tasks').then((m) => m.deleteTask(task.id));
    }
  });

  it('addTask validates then persists', async () => {
    const task = await addTask({ title: 'Ship release' });
    expect(task.id).toMatch(/^task_/);
    expect(task.status).toBe('todo');
    expect(await getTasks()).toHaveLength(1);
  });

  it('addTask throws ValidationError on an empty title', async () => {
    await expect(addTask({ title: '' })).rejects.toBeInstanceOf(ValidationError);
  });
});
