// HIDDEN verification test — applied to __tests__/__verify__/ after the session.
// Asserts the archive feature's contract (names are pinned by the task prompt).
import { describe, expect, it } from 'vitest';
import { createTask } from '../../app/api/tasks';
import { AppState } from '../../app/store/reducer';
import { selectActiveTasks, selectVisibleTasks } from '../../app/store/selectors';
import { Task } from '../../app/types';

function t(id: string, archived: boolean): Task {
  return {
    id, title: id, description: '', status: 'todo', priority: 'medium',
    assigneeId: null, createdAt: 0, updatedAt: 0, archived,
  };
}

const state: AppState = { filter: 'all', tasks: [t('a', false), t('b', true)] };

describe('[hidden] archive feature', () => {
  it('createTask defaults archived to false', async () => {
    const task = await createTask({ title: 'fresh' });
    expect(task.archived).toBe(false);
  });
  it('selectActiveTasks excludes archived tasks', () => {
    expect(selectActiveTasks(state).map((x) => x.id)).toEqual(['a']);
  });
  it('selectVisibleTasks excludes archived tasks', () => {
    expect(selectVisibleTasks(state).map((x) => x.id)).toEqual(['a']);
  });
});
