export function now(): number {
  return Date.now();
}

/** Human-friendly "x ago" string for a past timestamp. */
export function formatRelativeDate(ts: number, from: number = Date.now()): string {
  const seconds = Math.floor((from - ts) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
