/**
 * A tiny in-memory stand-in for a REST backend so the demo app runs without a
 * server. Each "collection" is a Map keyed by entity id. All access goes through
 * these helpers — api/tasks.ts and api/users.ts build on them.
 */
const collections: Record<string, Map<string, unknown>> = {};

function table(collection: string): Map<string, unknown> {
  if (!collections[collection]) {
    collections[collection] = new Map();
  }
  return collections[collection];
}

export async function apiList<T>(collection: string): Promise<T[]> {
  return Array.from(table(collection).values()) as T[];
}

export async function apiGet<T>(collection: string, id: string): Promise<T | null> {
  return (table(collection).get(id) as T) ?? null;
}

export async function apiPut<T extends { id: string }>(collection: string, item: T): Promise<T> {
  table(collection).set(item.id, item);
  return item;
}

export async function apiDelete(collection: string, id: string): Promise<boolean> {
  return table(collection).delete(id);
}
