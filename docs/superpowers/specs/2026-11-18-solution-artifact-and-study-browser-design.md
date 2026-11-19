# Phase 2 Solution Artifact and Study Browser Design

**Status:** Implemented
**Date:** 2026-11-18
**Roadmap:** P2.1–P2.10

## Purpose

Phase 2 adds a trustworthy path from an authorized solver output to a local,
bookmarkable Study screen. “Trustworthy” has two distinct meanings here:

1. PokerHelper can prove that every displayed decimal reproduces the pinned
   source output within the declared extraction tolerance.
2. PokerHelper tells the user what game the source did and did not model. It
   never promotes numerical fidelity to a claim of real-game GTO accuracy.

The bundled Phase 2 pack satisfies the first condition. Its source does not
provide an absolute error bound for a 100 BB cash game, so the pack remains
visibly marked approximate and may not be presented as accuracy-certified
grading. Phase 3 may use it only in an explicitly acknowledged
`REFERENCE_MODEL` mode whose EV loss is labelled relative to this exact pack.

## Bounded initial scenario

The first agreed tree represents the final two players at a six-max table after
UTG, HJ, CO, and BTN fold:

- 100 BB effective stacks;
- SB 0.5 BB and BB 1 BB, no ante;
- heads-up SB/Button against BB;
- SB fold, limp, raise to 2.5 BB, or all-in;
- subsequent raises are pot-sized after calling;
- at most four raises, with all-in always available where legal;
- no rake in the source model.

There are 18 public decision nodes and 34 terminal branches. This includes the
opening decision, limped pots, calls, checks, 3-bets, 4-bets, later raises, and
all-ins. It does not represent the other five six-max opening positions or the
approved MVP rake preset.

## Artifact layout

An artifact is a directory containing only declarative JSON:

```text
<artifact>/
  manifest.json
  nodes/
    node-000.json
    node-002.json
    ...
```

`manifest.json` is the root of trust. It records:

- schema and identity-profile versions;
- a typed SHA-256 solution ID;
- source owner, repository, full commit, and generation method;
- authorization basis, license, and redistribution permission;
- game, blind, stack, ante, position, and rake assumptions;
- action-tree sizing and raise cap;
- algorithm, iterations, equity samples and seed, realization factors, and EV
  baseline;
- exploitability inside the source model, extraction tolerances, extraction
  errors, and any absolute model-accuracy bound;
- limitations and explicit Trainer eligibility;
- scenario identity, assumed prior actions, root node, and every node-file hash.

The solution ID is `solution:sha256:<digest>`, where the digest covers the
canonical manifest payload excluding the ID itself. Because that payload
contains every node SHA-256, any meaningful change creates a different version.

## Node contract

Every decision node contains:

- actor, readable action history, pot, actor contribution, stack behind, and
  amount to call in BB;
- ordered legal source actions with stable IDs, action type, raise-to target,
  and `isAllIn` flag;
- action-to-child-decision links for navigable branches;
- all 169 grouped starting hands;
- all 1,326 exact two-card combos;
- reach, action frequency, and per-action EV for every exact combo;
- reach-weighted grouped frequencies and EVs derived from the exact combos.

Decimals are JSON strings. Frequencies are probabilities in `[0, 1]` and must
sum to one within `1e-9`. EV is decision-point net EV in BB: chips committed
before the current decision are excluded. This makes folding zero EV whenever
fold is legal and preserves a consistent baseline at check nodes.

Grouped values are presentation data only. Exact combos such as `AsKs` remain
the computational source, so suit-specific blocker differences are never lost.

## Validation and publication

Import is fail-closed and follows this order:

1. enforce manifest, per-file, total-size, and node-count limits;
2. require supported schema and identity versions;
3. require complete provenance and compatible redistribution permission;
4. constrain node paths to the artifact directory;
5. verify every node SHA-256 before parsing its content;
6. require unique nodes, actions, and valid child references;
7. require every possible exact combo exactly once at every node;
8. parse combos using the canonical card domain and verify group membership;
9. validate action sets, decimal strings, ranges, and normalization;
10. independently recompute all 169 grouped strategies from exact combos;
11. recompute the solution ID;
12. copy to staging, validate again, and atomically publish into the local
    content store.

Publishing an identical artifact twice is a no-op. A published solution
directory is never edited in place. The artifact directory is authoritative;
`index.json` is a rebuildable diagnostic catalog.

## Local API

The versioned API is read-only in Phase 2:

- `GET /api/v1/health`
- `GET /api/v1/version`
- `GET /api/v1/scenarios`
- `GET /api/v1/scenarios/{scenarioId}`
- `GET /api/v1/solutions/{solutionId}/assumptions`
- `GET /api/v1/solutions/{solutionId}/nodes/{nodeId}`

The server binds to `127.0.0.1`. It has no poker-client, screen-capture,
overlay, hand-watcher, telemetry, or hosted integration. Large node responses
use direct deterministic JSON serialization to stay within the local p95
budget.

## Study interface

The React Study browser provides:

- a validated-scenario selection screen;
- a complete list of all supported decision nodes;
- action buttons that follow every non-terminal branch;
- a keyboard-navigable 13×13 matrix with segmented action mixes;
- an exact-combo selector showing rank and suit;
- frequency and decision-point EV for every available action;
- stack, blinds, pot, amount to call, rake, history, and solution version;
- an assumptions drawer with source, license, configuration, convergence, EV
  baseline, integrity status, and limitations;
- URLs containing scenario, node, and optional exact combo.

The layout stacks at narrow widths, preserves exact-card and strategy details,
does not rely on color alone, supports arrow navigation in the matrix, exposes
visible focus, and honors reduced-motion preferences.

## Accuracy gates

The artifact declares two independent accuracy layers:

| Layer | Phase 2 result |
|---|---|
| Extraction fidelity to pinned source | max frequency error `6e-12`; max EV error `1e-12 BB` |
| Source-model convergence | `0.000802724936 BB/hand` exploitability |
| Absolute 100 BB game accuracy | no bound supplied |
| Accuracy-certified Trainer eligibility | `false` |

Representative exact-combo snapshots are fixed in automated tests. A common
node endpoint must remain below 200 ms p95 locally.

## Future extension

The schema supports additional immutable solution packs without changing Study
routes. A complete MVP cash-game pack must add the remaining six-max positions,
the approved rake model, sufficiently rich sizing, and a documented absolute
accuracy bound. Only a separately reviewed artifact meeting the Trainer
threshold may set `trainerEligible` to true.
