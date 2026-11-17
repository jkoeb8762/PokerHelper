# Phase 1 Implementation Backlog

**Status:** Approved and sequenced  
**Date:** 2026-11-17  
**Roadmap checkpoint:** P0.9  
**Estimate scale:** focused engineering time, not calendar commitment

## Delivery order

```text
F1 bootstrap
 ├─→ F2 exact values/errors
 ├─→ F3 cards/boards ─→ F4 evaluator
 └─→ F5 positions ─→ F6 betting/replay ─→ F7 rake
                    └─→ F8 combos/ranges
F2 + F3 + F6 + F8 ─→ F9 canonical identity
all features ───────→ F10 regression/CI/evidence
```

## F1 — Domain package and deterministic test harness

**Roadmap:** supports all P1 checkpoints  
**Estimate:** 0.5 day

Deliver:

- `backend/pyproject.toml` with a Python 3.12 compatibility floor;
- `src/pokerhelper/domain` package with no third-party imports;
- `unittest` discovery command and corpus-version marker;
- root developer commands and ignored local artifacts.

Accept when a clean standard-library Python installation can import the domain
and run the empty suite without network or database access.

## F2 — Exact decimals and structured domain failures

**Roadmap:** P1.9, dependency for P1.4/P1.5/P1.7/P1.8  
**Estimate:** 0.5 day

Deliver strict finite `Decimal` parsing/normalization and a stable `DomainError`
carrying `code`, `path`, `message`, and details. Reject floats, NaN, infinity,
and ambiguous values.

Accept when decimal equivalence, negative-zero, invalid-number, and error-shape
tests pass.

## F3 — Cards, exact combos, decks, and boards

**Roadmap:** P1.1  
**Estimate:** 1 day

Deliver ranks, suits, immutable cards, canonical exact-combo notation, a
52-card deck, and valid board construction. Reject duplicate/impossible states.

Accept when all `CARD-*` examples and exhaustive card/combo uniqueness
properties pass.

## F4 — Hold'em hand evaluator

**Roadmap:** P1.2  
**Estimate:** 1 day

Deliver exact five-card ranking and best-five-from-five-to-seven evaluation,
including wheels and deterministic tie-break tuples.

Accept when the independent `EVAL-*` reference fixture passes and category,
tie, and best-five properties hold.

## F5 — Six-max seats, positions, and action order

**Roadmap:** P1.3  
**Estimate:** 0.5 day

Deliver the fixed MVP position order, clockwise traversal, initial preflop
actor, and skip logic for folded/all-in seats.

Accept when all six starting points, skip combinations, and terminal cases pass.

## F6 — No-limit preflop replay and legal actions

**Roadmap:** P1.3, P1.4, P1.9  
**Estimate:** 3 days

Deliver game configuration, forced blinds, player state, action requests,
resolved actions, legal-action description, exact pot/stack accounting, turn
order, calls, checks, folds, full raises, short all-in raises, reopening rules,
round closure, and deterministic replay.

Accept when every `BET-*` golden prefix passes, all accounting invariants hold
after each prefix, and malformed actions fail with the expected code/path.

## F7 — MVP rake preset

**Roadmap:** P1.5  
**Estimate:** 0.5 day

Deliver versioned `MVP_CASH_5PCT_1BB_NFND_V1` policy and deterministic
qualifying-pot calculation with centi-BB rounding down.

Accept when all `RAKE-*` boundaries pass and preflop-only pots collect zero.

## F8 — 1,326 combos, 169 classes, and weighted ranges

**Roadmap:** P1.6, P1.7  
**Estimate:** 1.5 days

Deliver exhaustive combo generation, grouped-class mapping, deterministic
class ordering, sparse weighted ranges, exact normalization, aggregation, and
card removal.

Accept when counts per class are exhaustive, blocked-card counts match the
golden contract, and range operations preserve bounds and normalized sums.

## F9 — Canonical serialization and stable identities

**Roadmap:** P1.8  
**Estimate:** 1 day

Deliver semantic canonicalization for enums, dataclasses, decimals, mappings,
ordered histories, and sorted range entries; SHA-256 typed content IDs; and
state/config serialization helpers.

Accept when all `ID-*` equivalence/difference and round-trip cases pass across
supported Python versions.

## F10 — Full regression suite and continuous integration

**Roadmap:** P1.10 and Phase 1 exit gate  
**Estimate:** 1 day

Deliver:

- fixture loaders and readable golden-case subtests;
- exhaustive and property-style deterministic tests;
- Windows and Linux GitHub Actions matrix for Python 3.12 and 3.14;
- coverage of every stable error family used in Phase 1;
- README commands and roadmap evidence links.

Accept when the complete suite passes locally, the workflow is syntactically
valid and invokes the identical suite, no test uses network/time/random ambient
state, and Phase 1 exit criteria can be demonstrated from test output.

## Definition of done for every item

- Public values are immutable and typed.
- Canonical math never accepts binary floats.
- New rejection paths use stable codes and field paths.
- Examples and boundary tests accompany behavior.
- No framework, database, or filesystem dependency enters the domain package.
- Documentation and roadmap evidence are updated in the same change.

## Estimate summary

The initial Phase 1 implementation is roughly 10 focused engineering days for
one developer, with F6 carrying most rules risk. The backlog is deliberately
sequenced so each completed item remains useful if later work pauses.
