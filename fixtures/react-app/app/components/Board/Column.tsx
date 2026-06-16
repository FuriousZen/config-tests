import React from 'react';
import { Task, TaskStatus } from '../../types';
import { formatStatus } from '../../utils/format';
import { TaskCard } from '../TaskCard';

interface ColumnProps {
  status: TaskStatus;
  tasks: Task[];
}

export function Column({ status, tasks }: ColumnProps) {
  return (
    <section className="column">
      <h3 className="column-title">
        {formatStatus(status)} <span className="count">{tasks.length}</span>
      </h3>
      <div className="column-body">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </section>
  );
}
