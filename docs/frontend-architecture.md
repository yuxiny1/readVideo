# Frontend Architecture

The Angular frontend follows a Signals-at-the-view, RxJS-at-the-async-boundary design.

## Responsibilities

- Components own short-lived interaction state such as drag targets and open menus.
- Page-scoped facades own feature state and expose `signal` and `computed` values to containers.
- `ReadvideoApiService` is the only root data service. It is stateless and returns typed `Observable` values.
- Presentational components receive complete view models through `input()` and send user intent through `output()`.
- Pure selectors and parsers contain filtering, sorting, tag normalization, and Markdown rendering.

Page state services must be listed in the page or feature component `providers` array. Do not use
`providedIn: "root"` for state that belongs to New Video, History, Favorites, Reader, or Saved Sources.

## Signals And RxJS

- Use `signal` for current UI state and `computed` for derived state.
- Do not store values that can be derived from an existing signal.
- Keep HTTP, polling, and multi-request orchestration as Observable pipelines.
- Convert only at the component/facade boundary.
- Use `switchMap` for replaceable work, including task polling and dependent requests.
- Use `take(1)` for one-shot requests and `takeUntilDestroyed` for every facade subscription.
- Handle stream errors so a failed request does not silently kill future work.

## SOLID Boundaries

- **Single responsibility:** API transport, task presentation, model management, Reader parsing, Reader document state,
  and Reader library selection live in separate modules.
- **Open/closed:** New views consume typed view models without modifying the API transport layer.
- **Liskov substitution:** Components depend on stable data contracts rather than concrete page services.
- **Interface segregation:** Process Panel and Latest Output receive only the state and events they use.
- **Dependency inversion:** Containers coordinate facades; presentational components do not inject app services.

## Pull Request Checklist

- Every component uses `ChangeDetectionStrategy.OnPush`.
- API methods return typed Observables and do not use `fetch` or Promise wrappers.
- Page signals live in component-scoped providers.
- Presentational components use data-down/events-up inputs and outputs.
- Derived state uses `computed`; state updates are immutable.
- Templates use `@for (...; track ...)` and avoid expensive inline work.
- Subscriptions use `take(1)`, `takeUntilDestroyed`, or a template async boundary.
- Errors are handled inside the stream.
- New routes use lazy `loadComponent` loading.
- TypeScript modules stay below the repository's 350-line architecture guard.
