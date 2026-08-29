# TypeScript React Review Rules (Addon)

Used on top of `review-rules-typescript.md`. The severity definitions are the same as the base.
Never spend a finding on the React rules the linter already has on (`rules-of-hooks` and the
like).

## REACT: React Correctness

**Critical:** Derived state computed in an effect (it belongs in render or in a `useMemo`), logic
that belongs to an event handled in an effect, a stale closure that changes actual behavior, an
index key on a list that gets reordered
**Warning:** Subscribing to a whole store — calling `useXxxStore()` with no selector re-renders on
every change; local state duplicating a fact the store already holds; a new object, array, or
function identity passed to a memoized child on every render; effect dependencies missing or
excessive; a non-component export in a component file — Fast Refresh breaks (put constants,
helpers, and variant recipes in their own file)
**Info:** `useMemo`/`useCallback` with no performance basis

## STORE: Stores & Surfaces

**Critical:** Surface ownership violated on a store field — when one error or status field is
drawn by different routes or surfaces, split it into per-surface fields. **"Clear it on route
entry" is not a resolution** — reaching the wrong surface still happens and is merely hidden by
timing, so it comes back in a configuration where the two surfaces mount at once
**Warning:** A component subscribing to backend events directly — go through the store's connect
function (once at app start, returning a teardown). Re-subscribing on every mount multiplies
listeners; an action not clearing its own error field on success; business logic buried in a route
component → the store or `lib/`; direct coupling between stores
**Info:** Duplicated style class combinations

## P: Project-Specific

(Filled in at setup. If there are UI ownership rules such as an operations/configuration
boundary, make them entries pointing at the canonical document — `docs/design/ui-map.md` and the
like)
