# Design Principles

Type: code (design quality perspective)

The perspective you bring when reading a design. **This is not a scorecard** — it is not a
document where you mark each item compliant or not, but a set of axes for recognizing what gets
worse in a proposed structure.

- Write a finding as **what gets worse**. Never cite a principle's name as the rationale. Not
  "dependency direction violation" but "this arrangement only holds if the lower layer knows the
  upper one".
- Judgment is a matter of degree. Some designs put principles against each other; there, write
  what is lost and how much, then choose.
- Severity is set by the consequence — does implementing it as is damage the structure, or is it
  worth recording without blocking?
- Each axis needs different description. Never invent content to fill the same slot.

**Admission test**: an axis belongs here when ①it is about the structure itself (not about what
the document says), ②it concerns direction, placement, responsibility, or proliferation, and ③no
framework, API, or domain name appears in its body. Fail any of the three and it goes to the
coding rules document or to the spec authoring rules. **Never promote something encountered in
one piece of work into a new principle.**

## Direction of Dependency and Knowledge

The concrete depends on the abstract. A parent or shared type never queries a child's (a
derivative's or an implementor's) type or implementation. Module dependencies follow the existing
direction declared in {DEP_MANIFEST} and create no cycles. Where branching is needed, invert it
through a virtual function, an interface implementation, or a callback.

**What gets worse**: with the direction reversed, every change below drags a change above. When
the parent knows its children, the parent grows with every child added, and a new child can only
be added by editing the parent — the cost of extension rises with the number of derivatives. Once
there is a cycle, neither side can be read or tested on its own. Where this axis shows up in a
design: a parent that inspects its own type, shared logic that branches by derivative kind, a
module dependency running against the existing direction.

## Domain Neutrality of Shared Surfaces

A widely derived or widely called base type, shared function, or shared interface holds no state,
logic, or function declaration that only some of its derivatives or call sites use. That belongs
to the derivative that actually uses it, or to a type or function split out to do only that job.
What every derivative and call site uses is the base's responsibility.

**What gets worse**: every derivative and call site that does not use it carries it anyway, and
reading the base no longer tells you which consumer actually uses which member. A member on a base
class for one derivative, a function on an interface only some implementors fill in, and a branch
inside a general-purpose function for one call site are the first shapes of the violation.

## Separate Instead of Branching

A new use site is not a reason to add a use-site-specific branch to something that already has
derivatives or instances. Pull the overlapping part out of the existing thing and let the existing
use site and the new one each take it from there. Stacking one more base class on top of the
existing thing is not extraction.

**Whether to keep it one or split it is decided by the exposed surface — the methods, settings,
and data columns that callers and tools touch.** Using the same surface with only the values
changed means the same thing, and you make one more instance. A surface that differs even in part
means a different thing, and the overlap is what gets extracted.

**What gets worse**: as branches pile up, options grow faster than use sites and nobody knows
which combinations are actually used. It reaches a state where fixing one use site requires
checking the behavior of all the others, and the moment that check is past anyone's capacity,
nobody fixes it at all. One line of this-task-specific branching in a widely inherited base
method is the most common start, and an instance inheriting more than half its settings from
things unrelated to it means it is already well along.

## A Single Site of Handling

A new entry goes where existing entries of the same kind are already handled. When that site
cannot take the new entry's shape, extend the site rather than moving the handling elsewhere. The
site is not the table the entries are listed in — it is the code that reads and handles them.

**Extending means changing the site, not wedging in a condition for the new entry.** A site that
cannot take the new entry may have been built looking only at the first one. If only the values
differ, add it in the same shape. If the site has hardened around the first entry's circumstances,
fix the site so both go down the same path. If handling itself differs per entry, they are not
entries of the same kind and this is not their site.

**What gets worse**: once two places do the same job, nothing tells you which one already handled
it. A reader has to open both; a fixer fixes one. Whoever adds the next entry attaches it to
whichever place they saw first, so the two keep growing apart. Piling entries in the same shape
onto a hardened assumption produces a list that is uniform only on the surface — some entries are
read on one path only, and some do nothing at all when added, with no error. Confirming that the
existing site cannot take the new entry and concluding "let's handle it somewhere else" is the
most common start; if every other entry in a function has one shape and only this one is an
exception, or the conditions that make an entry valid differ per entry, it is already there.

## A Single Source of Truth

One state is kept in one place, and that place is the canon. Anywhere else that needs the state
reads the canon. When a copy is unavoidable — for performance, or because the value at some moment
has to be held — put one function that fills the copy from the canon, and let calling it be the
moment the copy is filled. Nothing outside that function writes to the copy, and the copy is never
written back to the canon.

**What gets worse**: when the two disagree, the code does not say which one is right. The
disagreement raises no error and flows on as a wrong value — the same amount added twice, or a
calculation run on a stale one. Adding a function that reconciles the two, or an "already applied"
flag to stop that, makes the two places something that must be fixed together from then on.
Keeping a second copy next to a consumer so it can use a value it does not own is the most common
start.

## Single Responsibility

A type has one reason to change. Reasons are counted from the side that demands the change —
whatever changes together under one demand is one reason. When state and logic that change for
different reasons sit in one place, split them. Where each part goes follows whoever actually
reads and writes that state.

**What gets worse**: with several reasons, touching it for one need puts the rest at risk
together, and because the scope of a change cannot be stated in advance, review does not hold up.
Nor can you stand up a test for one reason alone. When saying what a type does in one sentence
needs an "and", or when the name cannot say what it does and only points at a location, it usually
holds more than one thing.

## Flexibility Without a Requirement

Never pay for flexibility no requirement asks for. The targets are **speculative parameters,
extension points, settings, and branches**.

**Not targets**: names, boundaries, and abstractions themselves. Giving an implementation a name
and a place even with a single consumer, or introducing an abstraction to invert a dependency, is
not caught here. Whether an abstraction is there for inversion or for speculation is settled by
removing it — if the base would then have to know its derivatives it was inversion, and if nothing
changes it was speculation. Spilling an implementation into its call site with no name of its own
is not simplicity but concealment, and the next person builds the same thing again without even
knowing it exists.

**What gets worse**: unused flexibility sits unverified and usually does not fit at its first
real use. Meanwhile every reader has to read that branch and dismiss it. A virtual function with
one override, a callback with one subscriber, a setting only ever used at one value, and a
wrapping layer that only passes the call through are its shape. Opening things up in advance "to
make it easy to extend later" is the most common route, whereas the way to prepare for extension
is not to dig extension points in advance but to keep things separated ("Separate Instead of
Branching").

<!-- Attach project-specific axes below. For example: layer rules ("core is ignorant of the UI"), process boundaries -->
