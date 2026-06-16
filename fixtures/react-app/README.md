# Task Board (fixture)

A small but realistically layered React + TypeScript app, used as the workspace
for the OpenCode MCP-config experiment. The layering and cross-file call graph
are intentional — they give the codebase-memory / code-graph MCP servers
something to actually navigate.

## Architecture (data flows downward; UI calls upward)

```
components/  (Board, Column, TaskCard, TaskForm, common/)
   |  use
hooks/       (useTasks, useUsers, useDebounce)
   |  read from
context/AppContext  +  store/ (reducer, actions, selectors)
   |  call
services/    (taskService, userService, notificationService)
   |  call
api/         (tasks, users)  ->  api/client (in-memory backend)
   |  use
utils/       (validation, date, format, id)   types/ (task, user)
```

Representative relationships an MCP should surface:
- `utils/validation.validateTask` → used by `services/taskService.addTask` **and** `components/TaskForm`.
- `services/taskService.getTasks` → called by `context/AppContext.refresh`.
- `store/selectors.selectVisibleTasks` → used by `hooks/useTasks` → `components/Board`.
- `api/client.apiPut` → used by both `api/tasks` and `api/users`.

## Layout
- `app/` — source (entry: `app/main.tsx` → `app/App.tsx`)
- `__tests__/` — vitest suites mirroring `app/`’s folder layout
- `package.json` / `tsconfig.json` / `vitest.config.ts`

## Commands (reference)
```
npm install
npm test          # vitest
npm run typecheck # tsc --noEmit
```
