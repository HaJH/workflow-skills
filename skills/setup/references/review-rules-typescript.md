# TypeScript Review Rules

A review lens. It carries severity and detection patterns only. The canon for a **P** item is
`CLAUDE.md`, and CLAUDE.md wins when the two disagree. Never spend a finding on what the gate
(linter · `tsc` · formatter) rejects — if you see it, that is one line saying "the gate was not
run". Unused imports, formatting, and lint rule violations are not here.

If the project uses React, add `review-rules-typescript-react.md`.

## Severity

- **Critical** — must fix before merge (correctness, boundary violations)
- **Warning** — should fix; justify in report if rejected
- **Info** — advisory; fix or acknowledge

## TYPE: Type Quality

**Critical:** The payload type of an external boundary (IPC, API, file) redefined by hand —
import the generated type or the schema-inferred type (a hand-written copy silently goes out of
step when the other side changes); error branching by string-matching on `error.message` — branch
on a code or a type
**Warning:** `any`, an `as` assertion with no basis, a non-null assertion (`!`) — a narrowing
guard belongs there, a loose `string` where a union literal type exists, missing return type on an
exported function
**Info:** catch or parameter typed `any` instead of `unknown`

## ERR: Error Handling

**Critical:** The failure of an async action the caller discards as `void` ignored — catch it
inside and route it to the surface's error field (an unhandled rejection must not be the only
trace); empty catch
**Warning:** Error handling missing on external input or file I/O, loading/error state missing

## SEC: Security

**Critical:** Unsanitized HTML insertion (XSS), `eval`/`Function`, path traversal
**Warning:** File path unvalidated, hardcoded credential

## BOUNDARY: Boundaries (project-specific)

**Critical:** **P** A backend, IPC, or network call made directly outside the single gateway
module — the gateway's reason to exist quietly becomes a lie. Check at every new backend contact
point
**Critical:** **P** Proposing or performing a hand edit of a generated file (`*.gen.ts`,
bindings) — fix upstream and regenerate
**Warning:** Remote call inside a loop (N+1), an optimistic update racing the confirmed response —
the confirmed snapshot is the single source of truth

## STRUCT: Structure

**Warning:** Duplicated block of 3+ lines → a shared function or component, a module with mixed
roles → split along the role line, direct coupling between modules (depending on another module's
internal state)
**Info:** Hardcoded value (magic number or string)

## TEST: Testing

**Warning:** Public function with no test, a guard test that does not break when the guard is
reverted
**Info:** Missing edge case, snapshot tests over-relied on

## P: Project-Specific

(Filled in at setup. Give BOUNDARY's gateway path and the list of generated files as concrete
paths. Each entry is severity + detection pattern + `→ CLAUDE.md "Section"`)
