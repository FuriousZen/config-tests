import React from 'react';
import { useTasks } from '../../hooks/useTasks';
import { TaskStatus } from '../../types';
import { Column } from './Column';

const COLUMNS: TaskStatus[] = ['todo', 'in_progress', 'done'];

export function Board() {
  const { tasks } = useTasks();
  return (
    <div className="board">
      {COLUMNS.map((status) => (
        <Column key={status} status={status} tasks={tasks.filter((t) => t.status === status)} />
      ))}
    </div>
  );
}
