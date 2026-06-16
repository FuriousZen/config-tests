// HIDDEN verification test — applied to __tests__/__verify__/ after the session.
import { describe, expect, it } from 'vitest';
import { AppState } from '../../app/store/reducer';
import { selectTasksByStatus, selectVisibleTasks } from '../../app/store/selectors';
import { Task } from '../../app/types';

function t(id: string, status: Task['status']): Task {
  return {
    id, title: id, description: '', status, priority: 'medium',
    assigneeId: null, createdAt: 0, updatedAt: 0,
  };
}

const state: AppState = {
  filter: 'all',
  tasks: [t('a', 'todo'), t('b', 'in_progress'), t('c', 'in_progress'), t('d', 'done')],
};

describe('[hidden] selectTasksByStatus filters by the requested status', () => {
  it('in_progress returns only in_progress tasks', () => {
    expect(selectTasksByStatus(state, 'in_progress').map((x) => x.id).sort()).toEqual(['b', 'c']);
  });
  it('done returns only done tasks', () => {
    expect(selectTasksByStatus(state, 'done').map((x) => x.id)).toEqual(['d']);
  });
  it('todo still returns only todo tasks', () => {
    expect(selectTasksByStatus(state, 'todo').map((x) => x.id)).toEqual(['a']);
  });
  it('selectVisibleTasks honors a non-todo filter', () => {
    expect(selectVisibleTasks({ ...state, filter: 'done' }).map((x) => x.id)).toEqual(['d']);
  });
});
