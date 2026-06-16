Add an "archive task" feature to this Task Board app. It spans the whole stack —
implement each layer:

1. Type: add an `archived: boolean` field to `Task` in `app/types/task.ts`.
   New tasks must default to `archived: false` (see `app/api/tasks.ts:createTask`).
2. Service: add `archiveTask(task: Task)` to `app/services/taskService.ts` that
   persists the task with `archived: true` (reuse the existing api save path).
3. Store: add an `'ARCHIVE_TASK'` action in `app/store/actions.ts` and handle it
   in `app/store/reducer.ts`, and add a selector `selectActiveTasks(state)` in
   `app/store/selectors.ts` that excludes archived tasks.
4. Wire visibility: make `selectVisibleTasks` exclude archived tasks (so archived
   tasks disappear from the board).
5. UI: expose an `archiveTask` handler from `app/context/AppContext.tsx`, surface
   it through `app/hooks/useTasks.ts`, and add an "Archive" `Button` to
   `app/components/TaskCard/TaskCard.tsx` that calls it for the card's task.

Keep the style consistent with the surrounding code. Add or update tests where it
makes sense.
