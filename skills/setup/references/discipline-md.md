# docs/discipline.md Template (module: discipline)

Language-agnostic development discipline. Both Dev and Reviewer read it. Generate the following
as `{PROJECT_PATH}/docs/discipline.md`. The "Instruction Authoring Policy" applies so that a
project does not append its own anecdotes — only rules and symptoms grow.

```markdown
# Development Discipline

Applies to Dev and Reviewer alike. Each entry is a directive and a symptom. Anecdotes and
provenance stay in commit messages and reports and are never appended here
(`docs/workflow.md` "Instruction Authoring Policy").

## No Causal Claims Without Observation

**A causal story built by reading code is a hypothesis.** Before writing "the cause is
identified", ask whether that causality was confirmed by observation. If it was not, write
"hypothesis" and build the means to observe first.

- The means to observe is only useful once it has **a table that splits the branches** — assign
  to each branch the observation that settles it, and do not leave out the branch where "sender
  and receiver are both right and only the application is wrong". Symptom: there are logs, but
  what to look at and what to decide from it differs from person to person
- **Make the observation run print, in the same output, what it is measuring.** Symptom: the
  observation was honest but its target was not this branch's code (a cached module, a stale
  build, a window on another port)
- **When the gate fails out of step with the source, run the same command in another tree before
  fixing anything.** While a worktree exists, two trees hold the same commit, which separates a
  source cause from an artifact cause in one step. "It built, so it is current" is an assumption,
  not an observation
- **Run the same measurement against a control whose answer you already know.** This is the check
  on whether the ruler measures what you think it measures. Symptom: one stage across a pipe was
  counting something else (`grep -c '\r'` counts the letter r, not CR)
- **When the real measurement returns 0, pick a control whose known answer is not 0.** The dead
  return 0 to every question. First run the same command over a short fragment that is certainly
  in that file and see it come back 1 or more. Symptom: markdown emphasis, an inflection, or a
  line break got into the pattern and it returned 0 hits — when grepping prose, keep only the
  distinctive noun phrase
- **When you used an option that selects a range, print and count the selected set itself
  first.** Symptom: `--no-merges` still included commits that arrived through a merge (for direct
  commits only, use `--first-parent`)
- **When you write down a reproduction command, run it right there and compare against the
  output.** Pasting it is not a check. Symptom: the document says "this is exhaustive" or "this
  is the result after the fix" while the output of the command backing it is nowhere — write the
  hit count into the sentence

## The Only Time You May Ask the User — Observation

Ask only when you cannot pin the cause alone and need a log or a reproduction. It is securing the
means to observe, not outsourcing QA. When you ask, state **what to look at and what you will
decide from it** — "please take a look" is not an observation.

## What the Test Actually Supports

A pass is not evidence that the test supports anything. Symptoms: it calls around the gate and so
cannot catch a defect in the gate · the guard sits on an unreachable arm while the proving test
goes down another arm · the name is a general rule while the body asserts only a few fields.

1. **Revert it and watch it break.** After adding a guard or a branch, take it back out, run, and
   confirm that the test actually fails — then write that in the report. Sometimes not breaking is
   the answer — that is not a guard, it is restraint
2. **Remove guards one at a time.** Remove them together and which test supports which guard is
   gone
3. **What to revert is decided by "what does this test's name claim?"** Apply it only to things
   named "guard" and the places that feel like a "field" or a "mapping" slip through
4. **If the name carries a general rule, the body must be general too.** If the name says "all
   X", enumerate X and walk it
5. **Check that the test goes down the real path.** A test that calls an internal function
   directly supports only that function. At least one test must run the end-to-end path
6. **Whether a guard is reachable is decided by the condition at the call site.** Look only
   inside the function and the branch seems fine — trace back to the render and execution
   conditions at the call site and ask "what reaches this branch?"
7. **If you moved a guard, remove it at the new place.** Removing it at the old place confirms
   nothing. Symptom: the test was right, the guard slipped out from under it, and the light is
   still green
8. **A test helper that reimplements the target means the test does not support the target.** A
   helper calls the target; it does not imitate it

Collapse it when you can — make it take the consumer as a parameter and the compiler blocks by
arity. That is stronger than a test.

## Matching Is Not Correctness

Alongside the test that checks two consumers match, a shared definition must have one test that
**asserts directly what it means**. When both sides are wrong together, the cross test is always
green.

## Name Them, Do Not Count Them

A comment or document in the shape of **counting how many pieces of code exist** ("all eight
routes", "the two callers", "both", "the only") is true when written and turns false with the
light still green. Whoever adds a consumer reads code; they do not audit prose.

- **A comment justifying a shared definition writes who shares it, not how many.** If you cannot
  write the list, you do not actually know whether the sentence is true
- **Write a consumer list in a fixed notation** — `/// Consumers: a, b, c`. It becomes a set that
  grep gathers
- **Entries are call-site names.** Written by purpose ("for the card column"), it goes stale even
  when no call changed
- **Write where the list closes.** Point downstream and you must enumerate all of downstream. The
  cheap check: can you reproduce that list with one grep?
- **A hypothetical count is fine** — "three copies would diverge" cannot go stale
- Collapse it when you can — once the list is a type's constructor list, the compiler counts it

### Review Question — What Did This Commit Become a Consumer Of

You cannot catch it by finding the list and checking whether it is right. The moment of
divergence is **the commit that adds a new call site**, and there is no list on the call-site
side. So a branch review asks "what did this commit become a consumer of?", and where that target
carries a consumer list, checks whether this branch went into it. Its pair is "what did it stop
being a consumer of" — the search is easier because you know the removed name.

### Prose Sweep — Every Round

1. **Symbol sweep**: `git grep` for the symbols this round deleted or newly introduced. Then
   `grep -r docs/reports/` — reports are gitignored and so outside `git grep`'s range
2. **Number-word sweep**: `git diff main...HEAD | grep '^+' | grep -E '(two|three|four|both|all|
   only|every|sole|entire)'` — the target is the sentences this round newly wrote
3. **Category sweep**: if you added an entry to an enumerated category, sweep the whole file by
   that category's name ("exception", "consumer", "branch"). Lines an earlier round wrote are not
   in the added lines
4. **Vocabulary sweep**: sweep for a deleted symbol by the words prose called it too — not only
   the name, but also **what it sat next to** and **what it did**. When you write down a zero,
   write what the zero was about
5. **When ownership changes, read the whole document that covers that concept.** A document calls
   itself "this card" or "here", so it is not caught by its own name

The three branches share one root — **the check you believed you ran did not reach that place**:
range (that line was outside the target) · vocabulary (it was called something else) · execution
(it was never run). In every branch, "I swept it", "there are zero hits", and "I wrote it down"
finish out true, so nobody looks again.

## Comments — No Default

Code whose intent shows through its names, types, and structure is the canon. When an explanation
seems needed, first check whether the code can be made self-evident (rename, extract a function,
split a condition) before writing a comment.

**Comment on**: the derivation of a formula or algorithm, a non-obvious intent or constraint (why
the other natural way does not work), a trap warning, an external compatibility boundary.
**Never comment**: a restatement of what the name already says, a copy of something whose canon
is elsewhere, a description of what another file does, work provenance or issue numbers or
follow-up plans, commented-out code.

Three questions right before writing one:

1. **Does this comment go wrong when another file changes?** Then do not write it. If that "why"
   is genuinely needed, move it into code (a name, an extracted function, an assertion)
2. **Is it answering a review finding?** That rationale belongs in the report's Response. Written
   into the code as well, there are now two canons
3. **Is it because everything around it has one?** That is not a reason to comply

On finding a comment-code mismatch, consider **deletion before correction**. In review, a comment
finding covers **factual mismatch with the code only**, capped at one per review, with no effect
on the verdict.

## Documentation-Work Traps

- **Never write a path in through a heredoc** — a Windows path starting with `\v`, `\t`, or `\n`
  becomes a control character. Use the `Edit`/`Write` tools. Symptom: a character vanishes from
  the rendered document, reads as a typo, and `git diff` does not draw it either
- **Write preview and check output outside the repo.** Landing in the working tree, `git add -A`
  commits it
```
