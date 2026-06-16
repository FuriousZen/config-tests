Rename the service function `getTasks` in `app/services/taskService.ts` to
`loadTasks`. This is a cross-file rename: update the definition and EVERY call
site and reference across the codebase, including:

- `app/context/AppContext.tsx` (the `refresh` callback calls it)
- any tests under `__tests__/` that import or call it (e.g.
  `__tests__/services/taskService.test.ts`)

Find all usages — leave no reference to the old name behind. Do not rename the
underlying `app/api/tasks.ts:fetchTasks` (that is a different function); only the
service-layer `getTasks`. The app must still typecheck and the tests must still
pass after the rename.
