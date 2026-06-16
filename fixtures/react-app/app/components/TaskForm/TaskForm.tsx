import React, { useState } from 'react';
import { useTasks } from '../../hooks/useTasks';
import { NewTaskInput, TaskPriority } from '../../types';
import { validateTask } from '../../utils/validation';
import { Button } from '../common/Button';

export function TaskForm({ onDone }: { onDone?: () => void }) {
  const { createTask } = useTasks();
  const [title, setTitle] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [errors, setErrors] = useState<string[]>([]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const input: NewTaskInput = { title, priority };
    const result = validateTask(input);
    if (!result.valid) {
      setErrors(result.errors);
      return;
    }
    await createTask(input);
    setTitle('');
    setErrors([]);
    onDone?.();
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Task title"
      />
      <select value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)}>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>
      {errors.length > 0 && (
        <ul className="errors">
          {errors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      )}
      <Button type="submit">Add task</Button>
    </form>
  );
}
