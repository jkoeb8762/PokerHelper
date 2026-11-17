# Phase 1 Verification Evidence

**Date:** 2026-11-17  
**Environment verified:** Windows, Python 3.12.3  
**Corpus:** `EVAL_REFERENCE_V1` plus named `CARD`, `BET`, `POS`, `RAKE`,
`RANGE`, `ID`, `ERR`, and `PROP` tests

## Verification result

The deterministic Phase 1 command completed successfully:

```powershell
.\scripts\test.ps1
```

Result: **55 tests passed in 1.078 seconds**. A subsequent bytecode compilation
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
| P1.10 CI | `.github/workflows/domain-ci.yml` | Same command configured for Windows/Linux and Python 3.12/3.14; hosted run pending repository connection |

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

The GitHub Actions workflow is present and uses the identical deterministic
command, but this repository currently has no GitHub remote and this machine has
neither a GitHub Actions runner, Docker, nor `act`. Therefore the hosted
Windows/Linux × Python 3.12/3.14 matrix has not executed yet. P1.10 remains open
until the first connected run is green; no poker-domain defect is presently
known.

## Review entry points

1. Start with `game.py` and `test_game.py` for no-limit rule semantics.
2. Review `hand_evaluator.py` against the JSON reference corpus.
3. Review `ranges.py` for exact-combo/class counts and normalization.
4. Review `canonical.py` for semantic identity boundaries.
5. Run `scripts/test.ps1`, then inspect the four-job CI matrix.
