import { describe, expect, it } from 'vitest';
import { initialState, reducer } from '../../app/store/reducer';
import { Task } from '../../app/types';

function makeTask(id: string, overrides: Partial<Task> = {}): Task {
  return {
    id,
    title: `Task ${id}`,
    description: '',
    status: 'todo',
    priority: 'medium',
    assigneeId: null,
    createdAt: 0,
    updatedAt: 0,
    ...overrides,
  };
}

describe('reducer', () => {
  it('SET_TASKS replaces the task list', () => {
    const next = reducer(initialState, { type: 'SET_TASKS', tasks: [makeTask('1')] });
    expect(next.tasks).toHaveLength(1);
  });

  it('UPSERT_TASK inserts then updates by id', () => {
    let state = reducer(initialState, { type: 'UPSERT_TASK', task: makeTask('1') });
    expect(state.tasks).toHaveLength(1);
    state = reducer(state, { type: 'UPSERT_TASK', task: makeTask('1', { title: 'Renamed' }) });
    expect(state.tasks).toHaveLength(1);
    expect(state.tasks[0].title).toBe('Renamed');
  });

  it('REMOVE_TASK drops the matching task', () => {
    const start = reducer(initialState, { type: 'SET_TASKS', tasks: [makeTask('1'), makeTask('2')] });
    const next = reducer(start, { type: 'REMOVE_TASK', id: '1' });
    expect(next.tasks.map((t) => t.id)).toEqual(['2']);
  });
});
