# Rust Review Rules

A review lens. It carries severity and detection patterns only. The canon for a **P** item is
`CLAUDE.md`, and CLAUDE.md wins when the two disagree. Never spend a finding on what the gate
(`cargo fmt --check` · `clippy -D warnings` · `cargo test`) rejects — if you see it, that is one
line saying "the gate was not run".

## Severity

- **Critical** — must fix before merge (correctness, safety, security)
- **Warning** — should fix; justify in report if rejected
- **Info** — advisory; fix or acknowledge

## OWN: Ownership & Lifetimes

**Critical:** Unnecessary clone of large data, dangling reference, `'static` overused
**Warning:** Ownership transferred where a reference would do, unnecessary `Arc`/`Rc`

## ERR: Error Handling

**Critical:** `unwrap`/`expect`/`panic!` on a production path (with no `[lints]` in the
workspace, the clippy default allows it, so the gate does not catch it), errors swallowed
**Warning:** `?` propagated without context, `Box<dyn Error>` overused

## ASYNC: Concurrency

**Critical:** Missing `await`, `Send` bound not satisfied, possible deadlock
**Warning:** Unnecessary `block_on`, `unbounded_channel` used indiscriminately, synchronous I/O
inside async

## SEC: Security

**Critical:** Unverified `unsafe`, external input unvalidated, hardcoded secret
**Warning:** Missing `// SAFETY:` comment on an `unsafe`, argument escaping missing on a process
call

## QUAL: Code Quality

**Warning:** Function over 50 lines, nesting deeper than 4, `pub` over-exposed, magic number
**Info:** `todo!()` left in, missing type alias

## SERDE: Serialization

**Warning:** Missing `serde(default)`, `rename_all` inconsistent

## TEST: Testing

**Warning:** Public function with no test, hardcoded path (`tempdir` not used), a guard test that
does not break when the guard is reverted
**Info:** Test name does not describe the behavior

## P: Project-Specific

(Filled in at setup. The places that compile and pass the gate and still cause incidents — a
layer boundary violation, a license isolation violation, a hand-edited generated file. Each entry
is severity + detection pattern + `→ CLAUDE.md "Section"`)
