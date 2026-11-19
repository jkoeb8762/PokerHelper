# Phase 3 Verification Evidence

> **Release correction — 2026-11-19:** This evidence verifies Trainer mechanics
> against the SB-versus-BB reference fixture. It does not complete the original
> multi-position six-max MVP. Phase 3's release gate is blocked until reopened
> Phase 2 supplies and validates the approved strategy coverage.

**Phase:** Preflop Trainer

**Verified:** 2026-11-19

**Result:** MVP exit gate satisfied for the acknowledged SB-versus-BB reference model

## Shipped vertical slice

Phase 3 now runs locally from session setup through targeted review:

```text
validated immutable exact-combo solution
  → scenario / position / decision selection
  → reach-weighted exact hand
  → canonical-engine legal options
  → immediate or delayed choice recording
  → exact-decimal EV-loss feedback
  → durable SQLite session and immutable decision snapshot
  → filtered review / exact replay / repeat / targeted redrill
```

The implementation is deliberately honest about strategy quality. The bundled
pack remains `trainerEligible: false`; the user must acknowledge
`REFERENCE_MODEL` practice, and all feedback is labelled relative to immutable
solution version `phase2-hu-sb-bb-100bb-v1.1`. It is not presented as a full,
raked, accuracy-certified six-max GTO product.

## Checkpoint evidence

| Checkpoint | Evidence |
|---|---|
| P3.1 possible weighted combos | Standard prompts choose only positive-reach exact combos using exact-decimal reach-weighted sampling; zero-weight and empty ranges have unit regressions; targeted drills replay intentional exact node/combo pairs |
| P3.2 shared legal actions | `SolutionRuleValidator` replays every node and offered action through the Phase 1 engine for both Study and Trainer; it verifies pot, amount to call, contribution, stack, raise target, action type, and `isAllIn` |
| P3.3 exact EV loss | Policy v1 stores unrounded action EV strings and calculates `max(action EV) − selected action EV` with `Decimal`; boundary and API snapshot tests cover exact values |
| P3.4 frequency versus cost | Normalization tolerance (`1e-9`) is separate from the 1% material-support floor; “supported” also requires EV equivalence within `0.010 BB`, preventing finite-solve residue from overriding costly EV feedback |
| P3.5 actionable feedback | Immediate/replay screens show exact suits, choice, complete reference mix, action EVs, exact subtraction, severity, interpretation, combo reach, solution version, accuracy mode, node, and optional RNG record |
| P3.6 reproducible history | Session and every immutable decision persist solution ID/version, game configuration ID, scoring/sampling policy versions, offered/resolved actions, exact reference snapshot, accuracy mode, and timestamps |
| P3.7 review/filter/replay | Saved sessions provide severity filtering, EV-loss or sequence sorting, grouped breakdowns, priority review, and exact immutable decision replay; delayed sessions remain redacted until completion |
| P3.8 targeted drills | Mistake and close-decision redrills create provenance-linked sessions; browser acceptance reproduced the exact costly `Ac8h` node/combo in a `MISTAKE REVIEW` drill |
| P3.9 statistics/calibration | Tests cover volume, total/average/per-100 EV loss, severity, position/action/scenario/hand breakdowns, and a 50-comparable-decision calibration gate with observed/reference percentages |
| P3.10 end-to-end usability | Component tests plus the visible production-browser walkthrough cover deep-linked setup, acknowledgement, exact deal, all-in action, RNG, feedback, five-decision completion, filter, replay, redrill, responsive review, and hard reload |

## Persistence and privacy verification

Alembic migration `0001_phase3_training` creates the scenario catalog, sessions,
and decisions before writes are accepted. API restart tests verify that sessions
survive process restart and the catalog precedes session foreign keys. SQLite
uses foreign keys, WAL mode, a busy timeout, unique prompt/sequence constraints,
and short SQLAlchemy transactions.

Database triggers reject updates to saved decisions and completed session
scoring fields. Deleting a session cascades to its decisions transactionally;
a retained completed redrill safely detaches its optional source-session link.
Tests also confirm that active delayed feedback does not leak through session
summaries, decision replay, session lists, or all-time statistics.

All product-managed runtime files remain inside the repository:

- application data: `E:\PokerHelper\data` for the normal launcher;
- Python environment: `E:\PokerHelper\backend\.venv`;
- JavaScript dependencies: `E:\PokerHelper\frontend\node_modules`;
- setup/test/download caches: `E:\PokerHelper\.cache`;
- browser acceptance databases: ignored temporary directories below that cache.

The scripts may invoke Python or Node from an existing installation, but they do
not intentionally place PokerHelper dependencies, caches, builds, or study data
on `C:`.

## Automated verification

Final local release verification completed with:

- 87 backend tests passing in 43.242 seconds;
- all 23,868 exact combo/node records revalidated with content hashes;
- all 18 Study/Trainer nodes replayed through the canonical action engine;
- 4 frontend component tests passing;
- strict TypeScript compilation and production Vite build passing;
- locked Python dependency consistency (`pip check`, `uv lock --check`) passing;
- npm advisory audit reporting 0 known vulnerabilities;
- source distribution and wheel build passing, including Alembic files and all
  18 solution nodes;
- Trainer submission performance test passing its p95-under-300-ms contract.

The GitHub Actions workflow repeats the zero-dependency domain suite on Windows
and Ubuntu with Python 3.12 and 3.14, then installs locked Python 3.14 and Node
24 application dependencies, runs artifact/Study/Trainer/persistence tests,
tests the frontend, and builds the production bundle.

## Visible-browser acceptance

The production bundle was served by FastAPI at `127.0.0.1:8000` with a temporary
database under `E:\PokerHelper\.cache`. The following were observed in the
visible local browser:

- `/train?...&node=node-043` retained the requested BB decision instead of
  falling back to the entire tree;
- the resulting prompt showed exact `Ac8h`, correct 107.5 BB pot, 92.5 BB call,
  92.5 BB behind, and fold/call-all-in options;
- a 0.2% residual call with 16.741 BB loss was labelled a costly major mistake,
  while its raw frequency remained visible;
- five decisions completed and produced exact-combo history, priority review,
  totals, averages, per-100 results, and the BB-only action-sequence breakdown;
- the Major Mistake filter retained only the two matching rows;
- replay restored the immutable `Ac8h` reference snapshot and exact EV
  calculation;
- “Redrill mistakes” opened a ten-decision `MISTAKE REVIEW` beginning with the
  same exact `Ac8h` decision;
- a hard reload of the encoded session URL restored the same review;
- at a 390×844 viewport, document width stayed within the viewport, wide history
  and breakdown tables remained internally scrollable, and header actions had
  readable contrast.

The walkthrough found and resolved four issues before release: finite-solver
residue being described as support, a deep-linked node initialization race,
incorrect position metadata for a single-node drill, and mobile review overflow
plus header-button contrast.

## Exit-gate interpretation

The Phase 3 product mechanics are complete for the supported reference scenario:
a user can deliberately practice exact hands, receive reproducible solution-
relative feedback, review saved results, and drill weaknesses with no unresolved
critical poker-state or persistence defect.

This does **not** complete the first local MVP. A full six-max position and
action-sequence library, the approved cash rake preset, sufficient sizing, and
an accuracy-qualified solution source are required by reopened Phase 2 before
the Phase 3 release gate can pass.
