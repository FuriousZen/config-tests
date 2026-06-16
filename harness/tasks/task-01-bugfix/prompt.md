There is a bug in `app/store/selectors.ts`: `selectTasksByStatus(state, status)`
ignores the `status` argument and always returns tasks whose status is `'todo'`.

This corrupts everything downstream — `selectVisibleTasks` uses it, which feeds
`hooks/useTasks`, which drives the `Board`/`Column` rendering, so filtering by
"In Progress" or "Done" silently shows the wrong tasks.

Fix `selectTasksByStatus` so it filters by the requested `status`, and add a test
to `__tests__/store/selectors.test.ts` that covers the previously-broken case
(e.g. selecting `'in_progress'` or `'done'`). Do not change unrelated behavior.
