# Phase 3 Preflop Trainer Design

**Status:** Mechanics implemented; MVP release gate blocked by reopened Phase 2 coverage

**Date:** 2026-11-19

**Roadmap:** P3.1–P3.10

## Purpose and trust boundary

Phase 3 turns immutable solution nodes into repeatable, local practice. The
Trainer deals an exact two-card combo, accepts only actions that are legal at
that decision, scores the choice against the stored solution, and preserves
enough information to reproduce the result later.

The bundled strategy is useful as a reference-model vertical slice, but it is
not an accuracy-certified real-game GTO pack. It is rake-free, covers only SB
versus BB after four folds, and uses an approximate postflop realization model.
The user must acknowledge those limits before starting a session. UI and API
records carry `accuracyMode: REFERENCE_MODEL`, and feedback is described as
source-model EV loss. Future artifacts that meet the accuracy gate may use
`CERTIFIED` without changing the session contract.

## End-to-end flow

```text
validated immutable solution
  → choose scenario, position, node set, length, and feedback mode
  → create version-pinned local session
  → choose a node and reach-weight an exact combo
  → replay the node through the canonical legal-action engine
  → present exact suits and the engine-resolved options
  → record the user's choice and immutable reference snapshot
  → calculate exact-decimal EV loss and feedback policy labels
  → aggregate local session results
  → review, replay, repeat, or launch a targeted redrill
```

## Sampling and action validity

Standard sessions select uniformly among the user-selected decision nodes.
Within the selected node, only positive-reach exact combos can be dealt, and
their sampling probability is proportional to the solution's stored exact
combo reach frequency. Sampling converts decimal weights to integers before
drawing, avoiding binary floating-point drift. Targeted redrills intentionally
replay the exact node/combo pairs selected from prior decisions.

Study and Trainer share `SolutionRuleValidator`. It reconstructs the six-max
game configuration from the manifest, replays prior folds and the node action
history through the Phase 1 engine, verifies pot/call/stack metadata, and
resolves every offered fold, check, call, raise-to, and all-in flag. A mismatch
fails closed before the node is studied or trained.

## Scoring and interpretation

For each offered action, the decision stores the unrounded reference frequency
and decision-point EV in BB. Policy version 1 calculates:

```text
EV loss (BB) = highest offered action EV − selected action EV
```

All arithmetic uses `Decimal`; display rounding happens afterward. Severity is
based only on EV loss:

| EV loss | Severity |
|---:|---|
| `≤ 0.010 BB` | No material EV loss |
| `> 0.010` and `≤ 0.050 BB` | Small EV loss |
| `> 0.050` and `≤ 0.250 BB` | Significant mistake |
| `> 0.250 BB` | Major mistake |

Strategy status is separate. Frequencies at or above the 1% material-support
floor, at or below 5%, and within 0.010 BB of the best action are identified as
low-frequency but supported, so rarity is never treated as proof of a mistake.
Smaller values are treated as finite-solve noise for interpretation while their
exact value remains visible. Any action outside the material mix but within
0.010 BB of the best EV is labelled EV-equivalent; an action beyond that EV
tolerance is a costly deviation even when finite solving left a positive
frequency behind.

The optional RNG maps the reference mix to every integer from 1 through 100 by
the largest-remainder method. Stable action order breaks ties. The RNG is shown
only on request and never selects or submits an action.

## Feedback modes

Immediate mode reveals the reference mix, action EVs, exact calculation,
severity, interpretation, assumptions, combo reach, solution version, and any
shown RNG roll after each choice.

Delayed mode stores the same immutable decision but hides its strategy, EV,
severity, grouped breakdowns, and contribution to global statistics while the
session remains active. Ending or completing the session reveals the complete
review. This boundary is enforced by the service response, not only by the UI.

## Durable local model

SQLite is stored at `<repository>/data/pokerhelper.db`. Alembic migration
`0001_phase3_training` creates:

- `scenarios`, a local catalog of the immutable solution references;
- `training_sessions`, including scenario, solution ID and version, node and
  position selection, scoring/sampling policies, feedback mode, acknowledgement,
  pending prompt, summary, and drill provenance;
- `training_decisions`, including exact suits, grouped hand, offered and
  resolved actions, selected action, exact reference snapshot, EV loss, labels,
  RNG record, game configuration ID, solution identity, and timestamps.

SQLite foreign keys, WAL mode, a busy timeout, unique prompt/sequence
constraints, short transactions, and database triggers protect consistency.
Decision rows are immutable after insertion. Completed session scoring fields
are immutable, while a deleted source session may safely detach the optional
provenance link on a retained redrill. Deleting a session cascades to its own
decisions and summary in one transaction.

## Review and calibration

Session and all-time summaries report decision volume, total EV loss, average
EV loss per decision, EV loss per 100 decisions, severity counts, and
breakdowns by position, action sequence, scenario, and grouped hand. Review can
filter by severity, sort by cost or order, and replay the exact stored result.

Mistake redrills prioritize significant/major decisions, then measurable loss,
then the highest-loss available decisions. Close-decision drills select
material mixed actions whose top two action EVs are within 0.010 BB. Repeat
preserves the original selection.

Frequency calibration appears only after 50 comparable decisions with the same
scenario, content-addressed solution, node, grouped hand, and action set. It
shows observed versus average reference frequency and percentage-point
deviation; it is not inferred from unrelated situations.

## Local API

Phase 3 adds these endpoints under `/api/v1/training`:

- create, list, inspect, complete, repeat, and delete sessions;
- get the persisted active prompt and optionally reveal its RNG mapping;
- submit an offered action idempotently by prompt ID;
- replay a saved decision;
- create mistake or close-decision redrills;
- read aggregate statistics.

Strict request models reject extra fields and invalid enums. Domain failures
use stable structured error codes. The service binds only to `127.0.0.1`, has
no live-table input, and sends no study history or analytics externally.

## Verification strategy

Pure unit tests cover decimal scoring boundaries, low-frequency interpretation,
RNG allocation, and weighted sampling. API tests cover acknowledgement,
immediate/delayed disclosure, restart persistence, migration order, invalid
actions, immutable rows, deletion, redrills, calibration, and the 300 ms
feedback budget. Frontend component tests exercise setup-to-feedback and saved
review controls. The production build and a visible local-browser journey form
the release acceptance check.
