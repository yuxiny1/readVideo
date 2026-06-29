# Frontend Architecture

The Angular frontend follows a Signals-at-the-view, RxJS-at-the-async-boundary design, with NgRx SignalStore
for feature state that coordinates multiple related views and mutations.

## Directory Layout

The application uses a feature-first Angular structure:

```text
app/
  core/api/<unit>/                         Root HTTP transport
  features/<feature>/page/<unit>/          Route container quartet
  features/<feature>/data-access/<unit>/   Facade, store, or service pair
  features/<feature>/ui/<unit>/            Presentational component quartet
  features/<feature>/utils/<unit>/         Pure selector or parser pair
  features/<feature>/models/<unit>/        Feature-only contract pair
  shared/models/<unit>/                    Cross-feature contract pair
  shared/utils/<unit>/                     Cross-feature helper pair
```

Keep each spec beside its source and each TypeScript unit in its own directory. Visual component directories contain
exactly one `.component.ts`, `.component.html`, `.component.spec.ts`, and `.component.scss`. Non-visual units contain
their production `.ts` and colocated `.spec.ts`; they do not add empty templates. Do not place facades or stores in
`page/`, and do not add new files to the legacy top-level `components/`, `pages/`, `services/`, or `types/` directories.

## Responsibilities

- Components own short-lived interaction state such as drag targets and open menus.
- Page-scoped facades own interaction state and expose `signal` and `computed` values to containers.
- Component-scoped NgRx SignalStores own Favorites, Folders, Tags, and Reader document state.
- `ReadvideoApiService` is the only root data service. It is stateless and returns typed `Observable` values.
- Presentational components receive complete view models through `input()` and send user intent through `output()`.
- Pure selectors and parsers contain filtering, sorting, tag normalization, and Markdown rendering.

Page state services and SignalStores must be listed in the page or feature component `providers` array. Do not use
`providedIn: "root"` for state that belongs to New Video, History, Favorites, Reader, or Saved Sources. Favorites
and Reader each receive a lifecycle-bound `LibraryStore`; both use the same store contract and persistent API data
without keeping route-scoped UI state alive after navigation.

## Signals And RxJS

- Use `signal` for current UI state and `computed` for derived state.
- Do not store values that can be derived from an existing signal.
- Keep HTTP, polling, and multi-request orchestration as Observable pipelines.
- Use `withState`, `withComputed`, and `withMethods` to define SignalStore boundaries.
- Use protected SignalStore state and immutable `patchState` updates.
- Use `rxMethod` for Store HTTP mutations and handle errors inside each inner stream.
- Convert only at the component/facade boundary.
- Use `switchMap` for replaceable work, including task polling and dependent requests.
- Use `take(1)` for one-shot requests and `takeUntilDestroyed` for every facade subscription.
- Handle stream errors so a failed request does not silently kill future work.

## SOLID Boundaries

- **Single responsibility:** API transport, task presentation, model management, Library state, Reader parsing,
  Reader document state, and Reader library selection live in separate modules.
- **Open/closed:** New views consume typed view models without modifying the API transport layer.
- **Liskov substitution:** Components depend on stable data contracts rather than concrete page services.
- **Interface segregation:** Process Panel and Latest Output receive only the state and events they use.
- **Dependency inversion:** Containers coordinate facades; presentational components do not inject app services.

## Pull Request Checklist

- Every component uses `ChangeDetectionStrategy.OnPush`.
- API methods return typed Observables and do not use `fetch` or Promise wrappers.
- Page signals live in component-scoped providers.
- Shared feature state uses component-scoped NgRx SignalStore, not a root store.
- Presentational components use data-down/events-up inputs and outputs.
- Derived state uses `computed`; state updates are immutable.
- Templates use `@for (...; track ...)` and avoid expensive inline work.
- Subscriptions use `take(1)`, `takeUntilDestroyed`, or a template async boundary.
- Errors are handled inside the stream.
- New routes use lazy `loadComponent` loading.
- TypeScript modules stay below the repository's 350-line architecture guard.

## Unit Tests

- Angular unit tests use the Angular CLI `@angular/build:unit-test` builder with Vitest and jsdom.
- Every production `.ts` file under `frontend/angular/src` has a colocated `.spec.ts` file.
- Pure selectors and formatters test input/output behavior directly.
- Services test observable orchestration and HTTP method, URL, body, success, and failure contracts.
- SignalStores test state transitions, computed selectors, immutable updates, and request errors.
- Facades test user workflows with controlled API and router dependencies.
- Standalone components test inputs, outputs, initialization, and delegation without repeating facade tests.
- `npm run test:frontend:coverage` enforces 80% statements, 60% branches, 80% functions, and 80% lines globally.
