# Phase 1 Verification Evidence

**Date:** 2026-11-17  
**Environments verified:** Local Windows/Python 3.12.3 plus hosted Windows and
Ubuntu on Python 3.12 and 3.14
**Corpus:** `EVAL_REFERENCE_V1` plus named `CARD`, `BET`, `POS`, `RAKE`,
`RANGE`, `ID`, `ERR`, and `PROP` tests

## Verification result

The deterministic Phase 1 command completed successfully:

```powershell
.\scripts\test.ps1
```

Result: **55 tests passed in 1.090 seconds**. A subsequent bytecode compilation
check also completed without error:

```powershell
python -m compileall -q backend\src backend\tests
```

The tests have no network, clock, locale, database, or ambient-randomness
dependency. The one randomized property sample uses the fixed seed `1701`.

## Checkpoint traceability

| Checkpoint | Implementation | Executable evidence |
|---|---|---|
| P1.1 cards/decks/boards | `cards.py` | `test_cards.py` (`CARD-001`–`CARD-007`) |
| P1.2 hand evaluation | `hand_evaluator.py` | `hand-evaluation-reference-v1.json`, `test_hand_evaluator.py`, 200 seeded permutation cases |
| P1.3 positions/action order | `positions.py`, `game.py` | `POS-001`, `POS-002`, legal-frontier property |
| P1.4 betting/legal actions | `game.py` | `BET-001`–`BET-012`, legal-frontier replay property |
| P1.5 rake | `rake.py` | `RAKE-001`–`RAKE-006` |
| P1.6 1,326/169 mapping | `cards.py`, `ranges.py` | exhaustive `RANGE-001`, `RANGE-002` |
| P1.7 weighted ranges/removal | `ranges.py` | `RANGE-003`–`RANGE-009` |
| P1.8 serialization/IDs | `canonical.py` | `ID-001`–`ID-007` and replay identity property |
| P1.9 explicit rejection | `errors.py` and constructors/replay | `ERR-001`–`ERR-005` plus named invalid cases |
| P1.10 CI | `.github/workflows/domain-ci.yml` | [Domain CI run 44133021945](https://github.com/jkoeb8762/PokerHelper/actions/runs/44133021945): all four matrix jobs passed |

The legal-action frontier property explored more than 500 distinct prefixes to
depth six. Every generated legal action was accepted, each resulting state
reconciled stack and pot invariants, and replay produced the same stable state
ID.

## Performance smoke evidence

Measured after a warm run on the environment above:

| Operation | Observed p95 | P0.8 budget |
|---|---:|---:|
| Replay representative open/call prefix | 0.153 ms | under 2 ms |
| Generate and classify all 1,326 combos | 1.992 ms | under 100 ms |
| Canonically hash a representative state | 0.047 ms | under 5 ms |

These are smoke measurements, not a replacement for future benchmark tracking.

## Independent references and limitations

The hand-evaluation fixture encodes the category and best-five comparison rules
from the PokerStars Learn hand-ranking guide. Its expected tie-break tuples are
manually specified independently of PokerHelper's evaluator. P0.8 also requires
a large differential comparison with a separately maintained evaluator before
Phase 2 publication; that later release gate is intentionally not claimed here.

## Hosted CI evidence

GitHub Actions [Domain CI run 44133021945](https://github.com/jkoeb8762/PokerHelper/actions/runs/44133021945)
completed successfully against commit `6aa228426f4fc086ac11ca64e88b55c5b62713b1`.
It invoked the same deterministic command and passed all four jobs:

- Ubuntu / Python 3.12;
- Ubuntu / Python 3.14;
- Windows / Python 3.12;
- Windows / Python 3.14.

The run started at `2026-11-17T17:05:05Z` and completed at
`2026-11-17T17:05:27Z`. No artifacts or caches were produced. This satisfies
P1.10 and the Phase 1 executable verification gate.

## Review entry points

1. Start with `game.py` and `test_game.py` for no-limit rule semantics.
2. Review `hand_evaluator.py` against the JSON reference corpus.
3. Review `ranges.py` for exact-combo/class counts and normalization.
4. Review `canonical.py` for semantic identity boundaries.
5. Run `scripts/test.ps1`, then inspect the four-job CI matrix.
