import React, { createContext, useCallback, useContext, useEffect, useReducer } from 'react';
import { notify } from '../services/notificationService';
import * as taskService from '../services/taskService';
import { AppState, initialState, reducer } from '../store/reducer';
import { Action } from '../store/actions';
import { NewTaskInput, Task, TaskStatus } from '../types';

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  createTask: (input: NewTaskInput) => Promise<void>;
  moveTask: (task: Task, status: TaskStatus) => Promise<void>;
  refresh: () => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const refresh = useCallback(async () => {
    const tasks = await taskService.getTasks();
    dispatch({ type: 'SET_TASKS', tasks });
  }, []);

  const createTask = useCallback(async (input: NewTaskInput) => {
    const task = await taskService.addTask(input);
    dispatch({ type: 'UPSERT_TASK', task });
    notify(`Created "${task.title}"`);
  }, []);

  const moveTask = useCallback(async (task: Task, status: TaskStatus) => {
    const updated = await taskService.moveTask(task, status);
    dispatch({ type: 'UPSERT_TASK', task: updated });
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <AppContext.Provider value={{ state, dispatch, createTask, moveTask, refresh }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return ctx;
}
