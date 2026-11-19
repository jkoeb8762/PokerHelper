# Golden-Test Corpus and Accuracy Contract

**Status:** Approved for implementation  
**Date:** 2026-11-17  
**Roadmap checkpoint:** P0.8

## Purpose

This document defines what PokerHelper means by correct, deterministic, and
accurate. Implementations must satisfy this contract; tests may not redefine it
after observing implementation output.

## Test layers

1. **Examples:** named boundary and regression cases with exact expected output.
2. **Golden fixtures:** portable JSON inputs and expected semantic outputs.
3. **Properties:** invariants evaluated across generated or exhaustive inputs.
4. **Differential checks:** comparison with an independent implementation or
   authoritative reference where one exists.
5. **Round trips:** serialize, parse, replay, and re-score without semantic drift.

Golden fixtures are versioned product inputs. Changing an expected value
requires a written reason, an independent re-check, and a changelog entry.

## Numeric policy

### Canonical arithmetic

- BB amounts, weights, probabilities, frequencies, rake, and EV use Python
  `Decimal` created from strings or integers.
- Binary floats are rejected at canonical constructors.
- Decimal context precision is at least 50 significant digits for domain work.
- Equivalent finite representations normalize identically; NaN and infinity are
  invalid.
- Display rounding uses round-half-even and never feeds back into calculation.

### Exact and tolerance comparisons

| Quantity | Acceptance rule |
|---|---|
| Cards, positions, action order, statuses | Exact equality |
| Pot, stacks, contributions, call, raise target | Exact decimal equality |
| Canonical serialization and content ID | Byte-for-byte/hash equality |
| Range weight bounds | Exact `0 ≤ weight ≤ 1` |
| Normalized internal range | Exact sum `1` after deterministic residual assignment |
| Imported combo frequencies | Absolute sum error at most `1e-9` |
| Imported strategy EV | Absolute error at most `1e-6 BB` or the source's larger declared accuracy bound |
| Display frequency | One decimal place, half-even |
| Display decision EV/loss | Three decimal places, half-even |
| Hand rank | Exact category and exact tie-break tuple |

An artifact with a declared source bound worse than `1e-3 BB` is not eligible to
drive MVP feedback without a separate product decision.

## Golden-corpus inventory

Fixture IDs are stable and appear in test names and failure messages.

### Cards, deck, and board (`CARD-*`)

- All 52 rank/suit cards parse and round-trip.
- Unicode display and canonical two-character notation remain distinct.
- A fresh deck contains exactly 52 unique cards in canonical order.
- Duplicate hole or board cards fail with `POKER_RULE_DUPLICATE_CARD`.
- Board sizes 0, 3, 4, and 5 are accepted; 1, 2, and more than 5 fail.
- Exact combo canonicalization covers pair suit order and high-rank-first order.

### Hand evaluation (`EVAL-*`)

The reference pack includes every hand category, wheel and Broadway straights,
flush and straight kickers, double-trip full-house selection, three-pair
selection, board-playing ties, and best-five choice from seven cards.

Expected category order is:

```text
straight flush > four of a kind > full house > flush > straight
> three of a kind > two pair > one pair > high card
```

The category order and five-card comparison rules are sourced from the
[PokerStars beginner hand-ranking guide](https://www.pokerstarslearn.com/wp-content/uploads/2025/07/Beginners-Guide-To-Poker.pdf).
The fixture's tie-break tuples are independently reviewed against those rules,
not copied from PokerHelper output.

Before Phase 2, an exhaustive or large deterministic sample must be compared
against a separately maintained evaluator. Any disagreement blocks release.

### Positions and turn order (`POS-*`)

- Six-max seat order is `UTG, HJ, CO, BTN, SB, BB`.
- Initial preflop order is that same order beginning at UTG.
- Folded and all-in seats are skipped.
- A raise cycles action to the next eligible seat and eventually back to prior
  callers where required.
- A hand ends immediately when only one non-folded player remains.

### Betting and state replay (`BET-*`)

The pack includes:

- blinds only;
- open fold-through;
- limp/check;
- open/call;
- open/three-bet/fold;
- open/three-bet/call;
- full all-in raise;
- short all-in raise that does not reopen action;
- short all-in followed by a legal full raise from a player yet to act;
- all-in call;
- exact-stack call and under-call all-in;
- invalid check facing a wager;
- invalid call with nothing to call;
- invalid under-minimum non-all-in raise;
- invalid target beyond stack;
- action out of turn;
- action by folded/all-in player;
- deterministic replay and annotation mismatch.

For every accepted prefix:

```text
pot = sum(total contribution)
starting stack = stack behind + total contribution
amount to call = max(0, current wager - actor street contribution), capped by stack
```

### Rake (`RAKE-*`)

The MVP preset is `MVP_CASH_5PCT_1BB_NFND_V1`:

- rate `0.05`;
- cap `1 BB`;
- no-flop-no-drop enabled;
- collected from a qualifying postflop pot;
- round down to the nearest `0.01 BB` for the test model.

The corpus covers zero/negative rejection, no-flop zero rake, below-increment
amounts, exact increments, fractional calculations, and cap crossing. This is a
project preset, not a claim that it matches a particular poker site's current
rules. Solution artifacts must name the exact preset.

### Combo classes and ranges (`RANGE-*`)

- Exhaustively generate 1,326 unordered two-card combos.
- Map them to exactly 169 grouped classes.
- Each pair class has 6 combos, each suited class 4, and each offsuit class 12.
- Canonical examples include `KsKd → KK`, `AsKs → AKs`, `AhKc → AKo`.
- Duplicate entries, impossible weights, and blocked-card conflicts fail.
- Normalization is deterministic and sums exactly to 1.
- Removing one card leaves 1,275 possible unweighted combos; removing two
  distinct cards leaves 1,225.
- Aggregation weights exact combos rather than averaging class labels.

### Identity and serialization (`ID-*`)

- `2.5`, `2.50`, and `02.500` produce the same semantic serialization and ID.
- Negative zero becomes zero.
- Unordered maps and range entries sort canonically.
- Ordered action histories remain order-sensitive.
- A behaviorally meaningful change changes the content ID.
- Generated timestamps, descriptions, and the record's own ID do not affect a
  deterministic content ID.
- Parse/serialize and replay/serialize round trips are stable.

### Validation and errors (`ERR-*`)

Every rejection includes a stable family code, precise field path, readable
message, and safe details. Tests assert codes and paths, not full prose. No
canonical input is silently corrected.

## Strategy and Trainer accuracy policy

These tests become active when solution data is introduced:

- Every positive-reach exact combo has one result for every node option.
- Frequency sums meet the `1e-9` tolerance.
- Action EV exists even for a zero-frequency option if it can be graded.
- `EV loss = max(unrounded action EV) − selected unrounded action EV` exactly
  under canonical decimal arithmetic.
- Exact suits survive deal, feedback, persistence, review, and replay.
- The selected option must be both legal and offered by the node.
- Session summaries recompute from immutable decisions and do not trust caches.

### Feedback severity policy v1

| EV loss | Label |
|---|---|
| `≤ 0.010 BB` | No material EV loss |
| `> 0.010` and `≤ 0.050 BB` | Small EV loss |
| `> 0.050` and `≤ 0.250 BB` | Significant mistake |
| `> 0.250 BB` | Major mistake |

Threshold comparisons use unrounded EV loss. These are training-priority bands,
not moral judgments or claims about realized money.

Frequency normalization tolerance and strategy support are separate. Policy v1
uses `1e-9` only to validate that frequencies sum to one. An action is described
as materially supported only when its frequency is at least 1% and its EV is
within `0.010 BB` of the best offered action. A supported frequency at or below
5% is labelled low-frequency supported. Smaller residual frequencies remain
visible but are treated as finite-solve noise for interpretation; EV loss still
determines the mistake label.

Frequency calibration is displayed only after at least 50 comparable decisions
for the same scenario, exact/grouped aggregation key, action set, and solution
version. It always shows sample size and percentage-point deviation.

For integer RNG bands, frequencies are converted with the largest-remainder
method, node display order breaks ties, and the 100 assigned integers are
contiguous in display order. Exact frequencies remain separately inspectable.

## Performance budgets

Measured on the supported development baseline after one warm run:

| Operation | Budget |
|---|---|
| Replay a typical preflop action prefix | p95 under 2 ms |
| Generate/classify all 1,326 combos | under 100 ms |
| Canonically serialize and hash one state | p95 under 5 ms |
| Load a common local solution node (Phase 2) | p95 under 200 ms |
| Submit and render Trainer feedback (Phase 3) | p95 under 300 ms |

Correctness gates take precedence. A failed budget is recorded and profiled; it
never justifies bypassing validation.

## Determinism and platforms

- The same fixtures run on Windows and Linux.
- CI exercises Python 3.12 and 3.14.
- Tests set no locale or local-time dependency.
- Random/property tests use recorded deterministic seeds on failure.
- The core suite has no network dependency.

## Completion evidence

P0.8 is complete when this policy exists. Each later checkpoint is complete only
when its relevant fixture and property groups are executable in CI and the test
report identifies the corpus version.
