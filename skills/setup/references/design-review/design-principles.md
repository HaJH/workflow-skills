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

A widely derived or widely called base type, shared function, or shared interface holds no logic
or state belonging to one domain. Domain capability belongs to the type that implements that
domain, or to a dedicated unit.

**What gets worse**: every derivative and call site that does not use that domain carries the
knowledge anyway. The shared surface grows with each added domain, until it is no longer possible
to tell by reading which consumer actually uses what. Domain members attached to a base type and
domain branches inside a general-purpose function are where it starts.

## Separate Instead of Branching

A new use site is not a reason to add a use-site-specific branch to something that already has
derivatives or instances. Extract the common part and let the new use site compose it on its own
side.

**Whether to keep it one or split it is decided by the exposed surface.** Same surface with only
the values changed means the same thing plus an instance; a different surface means a different
thing.

**What gets worse**: as branches pile up, options grow faster than use sites and nobody knows
which combinations are actually used. It reaches a state where fixing one use site requires
checking the behavior of all the others, and the moment that check is past anyone's capacity,
nobody fixes it at all. One line of this-task-specific branching in a widely inherited base
method is the most common start, and an instance inheriting more than half its settings from
things unrelated to it means it is already well along.

## Single Responsibility

A type has one reason to change. When state and logic that change for different reasons sit in
one place, split them. Where each part goes follows whoever actually uses that data.

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
not caught here. Burying something where it cannot be found is not simplicity but concealment, and
the next person builds the same thing again without even knowing it exists.

**What gets worse**: unused flexibility sits unverified and usually does not fit at its first
real use. Meanwhile every reader has to read that branch and dismiss it. Virtual functions,
callbacks, and settings with a single consumer, and wrapping layers with no purpose, are its
shape. Opening things up in advance "to make it easy to extend later" is the most common route,
whereas the way to prepare for extension is not to dig extension points in advance but to keep
things separated so a new use site can compose its own.

<!-- Attach project-specific axes below. For example: layer rules ("core is ignorant of the UI"), process boundaries -->
