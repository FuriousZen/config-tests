import { Task, TaskStatus } from '../types';
import { Action } from './actions';

export interface AppState {
  tasks: Task[];
  filter: TaskStatus | 'all';
}

export const initialState: AppState = {
  tasks: [],
  filter: 'all',
};

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_TASKS':
      return { ...state, tasks: action.tasks };
    case 'UPSERT_TASK': {
      const exists = state.tasks.some((t) => t.id === action.task.id);
      const tasks = exists
        ? state.tasks.map((t) => (t.id === action.task.id ? action.task : t))
        : [...state.tasks, action.task];
      return { ...state, tasks };
    }
    case 'REMOVE_TASK':
      return { ...state, tasks: state.tasks.filter((t) => t.id !== action.id) };
    case 'SET_FILTER':
      return { ...state, filter: action.status };
    default:
      return state;
  }
}
