type Listener = (message: string) => void;

const listeners: Listener[] = [];

export function subscribe(listener: Listener): () => void {
  listeners.push(listener);
  return () => {
    const index = listeners.indexOf(listener);
    if (index >= 0) listeners.splice(index, 1);
  };
}

export function notify(message: string): void {
  for (const listener of listeners) {
    listener(message);
  }
}
