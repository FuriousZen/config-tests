// HIDDEN verification test — applied to __tests__/__verify__/ after the session.
import { describe, expect, it } from 'vitest';
import * as svc from '../../app/services/taskService';

describe('[hidden] taskService.getTasks was renamed to loadTasks', () => {
  it('loadTasks exists and returns an array', async () => {
    expect(typeof (svc as Record<string, unknown>).loadTasks).toBe('function');
    const result = await (svc as unknown as { loadTasks: () => Promise<unknown[]> }).loadTasks();
    expect(Array.isArray(result)).toBe(true);
  });
  it('the old getTasks name no longer exists on the service', () => {
    expect((svc as Record<string, unknown>).getTasks).toBeUndefined();
  });
});
