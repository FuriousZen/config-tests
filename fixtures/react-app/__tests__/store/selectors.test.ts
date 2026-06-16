import { describe, expect, it } from 'vitest';
import { AppState } from '../../app/store/reducer';
import { countByStatus, selectAllTasks } from '../../app/store/selectors';
import { Task } from '../../app/types';

function makeTask(id: string, status: Task['status']): Task {
  return {
    id,
    title: `Task ${id}`,
    description: '',
    status,
    priority: 'medium',
    assigneeId: null,
    createdAt: 0,
    updatedAt: 0,
  };
}

const state: AppState = {
  filter: 'all',
  tasks: [makeTask('1', 'todo'), makeTask('2', 'in_progress'), makeTask('3', 'done')],
};

describe('selectors', () => {
  it('selectAllTasks returns every task', () => {
    expect(selectAllTasks(state)).toHaveLength(3);
  });

  it('countByStatus tallies each status', () => {
    expect(countByStatus(state)).toEqual({ todo: 1, in_progress: 1, done: 1 });
  });
});
