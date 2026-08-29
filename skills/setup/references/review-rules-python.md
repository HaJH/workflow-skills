# Python Review Rules

A review lens. It carries severity and detection patterns only. The canon for a **P** item is
`CLAUDE.md`, and CLAUDE.md wins when the two disagree. Never spend a finding on what the gate
(`ruff` · `ruff format --check` · `mypy` · `pytest`) rejects — if you see it, that is one line
saying "the gate was not run".

## Severity

- **Critical** — must fix before merge (correctness, safety, security)
- **Warning** — should fix; justify in report if rejected
- **Info** — advisory; fix or acknowledge

## TYPE: Type Safety

**Critical:** `Any` overused, type hints entirely missing on a public function
**Warning:** `None` accessed without handling `Optional`, type hints partly missing
**Info:** `TypeVar` unused in a generic pattern

## ERR: Error Handling

**Critical:** bare `except` + `pass`, external API errors unhandled, empty except block
**Warning:** File I/O errors unhandled, re-raise without logging
**Info:** `Exception` instead of a specific exception

## SEC: Security

**Critical:** Hardcoded API key or secret, SQL injection, `eval`/`exec`
**Warning:** User input unvalidated, sensitive data in a debug log

## QUAL: Code Quality

**Warning:** Function over 50 lines, nesting deeper than 4, magic number
**Info:** Missing public docstring, f-string not used

## ASYNC: Concurrency

**Critical:** Missing `await`, synchronous I/O inside an async loop
**Warning:** `time.sleep` instead of `asyncio.sleep`

## TEST: Testing

**Warning:** Public function with no test, hardcoded path (`tmp_path` not used), a guard test that
does not break when the guard is reverted
**Info:** Missing edge case, mocks overused

## P: Project-Specific

(Filled in at setup. The places that pass the gate and still cause incidents. Each entry is
severity + detection pattern + `→ CLAUDE.md "Section"`)
