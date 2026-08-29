# C++ Unreal Engine Review Rules (Addon)

Used on top of `review-rules-cpp.md`. The severity definitions are the same as the base. The
canon for a **P** item is the project's coding rules document.

## NC-UE: UE Naming Conventions

**Warning:** Missing UE prefix on a class or struct (A/U/F/I/E/T/S), type prefix included in the
file name
**Info:** A Blueprint-exposed function name that is unclear from the BP user's point of view

## FMT-UE: Formatting

**Critical:** **P** Decorative non-ASCII characters (`—` `–` `→` `§`) in C++ source — MSVC reads
a file without a BOM in the local codepage and the compile breaks. Non-ASCII comment text itself
is allowed
**Critical:** A `*/` sequence inside a block comment body — the comment ends there and the text
after it is parsed as code

**Check pattern**: scan all code and comments for non-ASCII (excluding natural-language comment
text). `*/` inside a `/* … */` span.

## UE: Unreal Engine Specific

**Critical:** Replication code in a single-player project (`Replicated`, `Server`, `Client`,
`NetMulticast`)
**Warning:** Missing `UPROPERTY()` on a UObject member (not GC-tracked), missing `Category` on a
Blueprint function, virtual call in a constructor or destructor, missing `TEXT()` on a string
literal
**Info:** Tick enabled unnecessarily

## R-UE: UE Resource Management

**Critical:** Loading an asset directly (use the registry / GameData pattern), wrong Outer on
`NewObject`/`CreateDefaultSubobject`, holding an interface raw pointer as a member (not
GC-trackable — hold the actor instead)
**Warning:** `LoadSynchronous()` on the normal path in gameplay code (Tick, Notify, ability) —
use a hard reference or preload. A fallback after a failed `Get()` is allowed, and editor-only
code is exempt

## GAS: Gameplay Ability System (when applicable)

**Critical:** Raw GAS patterns used directly (must go through the wrapper), hardcoded
GameplayTag
**Warning:** Direct access to AbilitySystemComponent (go through the subsystem or interface)

## IF: Interface & Casting

**Warning:** **P** `Cast<ConcreteClass>` / `Cast<IInterface>` — go through the project's
interface helper. Look at the whole function you touched, not only the changed lines

## MOD-UE: Module Dependencies

**Critical:** Circular dependency, `#include` of a module not registered in `.Build.cs`
**Warning:** Violation of the one-way dependency flow, unnecessary module dependency added

**Check pattern**: take the module from the file path (`Source/<Module>/`) and read
`Public/PrivateDependencyModuleNames` in its `.Build.cs` — **the `.Build.cs` is the canon** and
the architecture document is an overview.
