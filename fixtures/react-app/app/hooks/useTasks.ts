import { useMemo } from 'react';
import { useAppContext } from '../context/AppContext';
import { countByStatus, selectVisibleTasks } from '../store/selectors';

export function useTasks() {
  const { state, createTask, moveTask, refresh } = useAppContext();
  const tasks = useMemo(() => selectVisibleTasks(state), [state]);
  const counts = useMemo(() => countByStatus(state), [state]);
  return { tasks, counts, createTask, moveTask, refresh, filter: state.filter };
}
