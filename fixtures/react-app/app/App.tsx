import React, { useState } from 'react';
import { Board } from './components/Board';
import { Button } from './components/common/Button';
import { Modal } from './components/common/Modal';
import { TaskForm } from './components/TaskForm/TaskForm';
import { AppProvider } from './context/AppContext';

export function App() {
  const [formOpen, setFormOpen] = useState(false);
  return (
    <AppProvider>
      <div className="app">
        <header className="app-header">
          <h1>Task Board</h1>
          <Button onClick={() => setFormOpen(true)}>New task</Button>
        </header>
        <Board />
        <Modal open={formOpen} onClose={() => setFormOpen(false)}>
          <TaskForm onDone={() => setFormOpen(false)} />
        </Modal>
      </div>
    </AppProvider>
  );
}
