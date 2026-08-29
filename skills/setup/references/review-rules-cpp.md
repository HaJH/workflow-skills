# C++ Review Rules

A review lens. It carries severity and detection patterns only. The canon for a **P** item is
`CLAUDE.md` (or the project's coding rules document), and the canon wins when the two disagree.
Never spend a finding on what the compiler, clang-tidy, or the formatter rejects — if you see it,
that is one line saying "the gate was not run".

Engine and framework rules are added through an addon file
(`review-rules-cpp-<framework>.md`).

## Severity

| Severity | Criteria |
|---|---|
| **Critical** | Runtime error, broken build, policy violation (exception use, `new`/`delete`, uninitialized pointer) |
| **Warning** | Guideline violation, maintainability (naming, missing `const`/`override`/`explicit`) |
| **Info** | Improvement suggestion |

## NC: Naming Conventions

**Warning:** PascalCase not followed, bool variable missing the `b` prefix, function name not
starting with a verb, out parameter missing the `Out` prefix
**Info:** Excessive abbreviation (under 3 characters outside loop variables)

**Check pattern**: class declarations, bool variables, function names, non-const `&` parameters.

## FMT: Formatting

**Critical:** **P** Anonymous namespace — under a Unity Build merge, same-named symbols collide
and the build breaks (Unity Build projects only)
**Warning:** Missing `#pragma once`, inconsistent opening brace placement, mixed tabs and spaces,
several variables declared on one line, file-scope `using namespace`
**Info:** Missing braces on a single-statement if/else

**Check pattern**: `namespace {`, `using namespace` at file scope, `{` at end of line.

## ES: Expressions & Statements

**Critical:** `NULL`/`0` as a pointer value (→ `nullptr`), `const_cast`, uninitialized pointer
**Warning:** Missing `override` on a virtual override, missing `explicit` on a single-argument
constructor, missing `const` on a member function that does not change state, `auto` for a
pointer type (→ `auto*`), `typedef` (→ `using`)
**Info:** Variable declared far from its use, unnamed magic constant (0/1/true/false excepted)

**Check pattern**: `= NULL`, pointer `= 0`, `virtual` without `override`, single-parameter
constructors.

## EH: Error Handling

**Critical:** `throw`/`try`/`catch` (under a no-exceptions policy), pointer dereference with no
null check
**Warning:** Missing precondition assertion on a function

**Check pattern**: Grep `throw `, `try {`, `catch (`.

## R: Resource Management

**Critical:** Direct `new`/`delete` or `malloc`/`free` outside a resource-management class
**Warning:** Raw pointer member with unclear ownership, resource acquisition without RAII

**Check pattern**: Grep `= new `, `delete `, `malloc(`, `free(`.

## TEST: Testing

**Warning:** Public function with no test, a guard test that does not break when the guard is
reverted
**Info:** Missing edge case

## P: Project-Specific

(Filled in at setup. The places that compile and pass the gate and still cause incidents — a
bypassed wrapper, module dependency direction, fail-safe handling. Each entry is severity +
detection pattern + `→ canon "Section"`)
