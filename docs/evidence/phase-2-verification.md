# Phase 2 Verification Evidence

**Phase:** Solution Pipeline and Study Browser
**Verified:** 2026-11-18; artifact maintenance revalidated 2026-11-19
**Result:** Exit gate satisfied for the agreed SB-versus-BB reference tree

## Shipped vertical slice

Phase 2 now runs locally from source to screen:

```text
pinned authorized solver
  → deterministic exact-combo generation
  → content-addressed JSON artifact
  → strict integrity and semantic validation
  → atomic local publication
  → versioned FastAPI reads
  → bookmarkable React Study browser
```

The bundled artifact is:

```text
solution:sha256:1d88317f8e6038ea071ef81b77151674b791dcfe817e1b121449711e469e9f6d
```

It contains 18 decision nodes, 169 grouped hands per node, and all 1,326 exact
combos per node. Total artifact size is 8,748,304 bytes.

## Checkpoint evidence

| Checkpoint | Evidence |
|---|---|
| P2.1 authorized source | Pinned `chirenonhive/poker-solver` commit `6d54d3…`, MIT authorization, provenance manifest, source decision, and third-party notice |
| P2.2 metadata | Schema v1 manifest covers source, license, game, rake, tree, solver, accuracy, EV baseline, limitations, Trainer eligibility, node hashes, and typed content ID |
| P2.3 rejection | Tests mutate frequencies, combos, action types, hashes, unknown files, and Trainer accuracy; all fail with stable structured codes |
| P2.4 deterministic import | Atomic staging validates before and after copy; a repeated import returns the same solution and creates one immutable directory |
| P2.5 navigation | UI lists all 18 nodes and links every non-terminal fold/limp/check/call/raise/all-in continuation; browser walkthrough covered open → 3-bet and direct node navigation |
| P2.6 range matrix | 13×13 keyboard grid renders all 169 reach-weighted grouped strategies; backend independently recomputes groups from exact combos |
| P2.7 exact combo | Exact suit selector preserves entries such as `AsKs`; the browser displayed its fold/call/raise/all-in frequencies and EVs at multiple nodes |
| P2.8 assumptions | Stack, blinds, pot, call amount, actor stack, no-rake source model, history, version, source, convergence, EV baseline, and limitations are visible |
| P2.9 source match | Generator compares every grouped node to the solver extractor; max frequency difference `6e-12`, max EV serialization difference `1e-12 BB`; representative snapshots are fixed in tests |
| P2.10 performance | 30 warmed root-node API reads: median `2.116 ms`, p95 `2.514 ms`, max `2.629 ms` against the `200 ms` contract |

## Solver and accuracy record

| Measurement | Result |
|---|---:|
| CFR+ iterations | 800 |
| Equity samples per canonical matchup | 8,000 |
| Deterministic equity seed | 1 |
| Source-model exploitability | 0.000802724936 BB/hand (0.803 mbb/hand) |
| Extraction frequency tolerance | 1e-9 |
| Extraction EV tolerance | 1e-6 BB |
| Observed max frequency error | 6e-12 |
| Observed max EV error | 1e-12 BB |
| Absolute real-game error bound | unavailable |
| Trainer eligibility | false |

Convergence and extraction fidelity do not remove the source model's limits.
Flop-going leaves use realized-equity factors instead of solved postflop play,
and the source is rake-free. The Study UI exposes those limits on every node.

## Automated verification

Local release verification completed with:

- 69 backend tests passing, including all Phase 1 domain tests;
- 2 frontend component tests passing;
- strict TypeScript compilation and production Vite build passing;
- npm advisory audit: 0 known vulnerabilities;
- immutable artifact validation over all 23,868 node/combo records;
- hard-refresh test for a nested bookmarked Study URL;
- source snapshot comparisons for root, versus-open, and versus-3-bet nodes.

GitHub Actions repeated the four-platform deterministic domain matrix plus the
locked Python 3.14 / Node 24 application suite. All five jobs passed in
[run 44415815675](https://github.com/jkoeb8762/PokerHelper/actions/runs/44415815675)
at commit `a078d69`; the application job installed from the lockfile, ran the
artifact and API checks, tested the UI, and built the production bundle.

During Phase 3, replaying every published option through the canonical engine
found that several stack-closing calls had correct amounts but stale
`isAllIn: false` metadata. The generator now derives the flag from the resolved
stack, the complete pack was deterministically regenerated as version
`phase2-hu-sb-bb-100bb-v1.1`, and all 18 nodes pass shared Study/Trainer poker
replay validation. Strategy frequencies and EVs did not change. The maintenance
artifact is the content ID and byte count recorded above; the hosted Phase 2 run
remains historical evidence for the earlier artifact, while current release
verification is recorded with Phase 3.

## Live-browser acceptance

The production build was served by FastAPI at `127.0.0.1:8000` and exercised in
the visible local browser. Verified interactions:

- scenario catalog loads the validated 18-node pack;
- root Study view displays the complete 13×13 matrix;
- default exact combo is `AsAh` and selecting `AKs` updates the URL;
- selecting `AsKs` preserves exact suits and changes displayed strategy;
- “Raise to 2.5 BB” navigates to `node-028` with the combo retained;
- displayed `AsKs` values at that node match the artifact snapshot;
- assumptions drawer reports no rake, the pinned source, MIT license, 800
  iterations, 0.803 mbb/hand, EV baseline, and every limitation;
- arrow-right moves keyboard focus from `AA` to `AKs`;
- reloading the deep URL keeps `node-028` and `AsKs` after the SPA fallback fix;
- the narrow layout places exact-combo details before the scroll-contained
  range matrix without page-level horizontal overflow.

## Exit-gate interpretation

The exit gate is satisfied for the explicitly agreed Phase 2 tree: any of its
18 SB/BB decision scenarios can be selected or reached through an action,
inspected at grouped and exact-combo levels, bookmarked, and reproduced from a
validated immutable artifact.

This is not an accuracy-certified, full six-max Trainer pack. Phase 3 permits
it only as an explicitly acknowledged `REFERENCE_MODEL` and labels EV loss
relative to this exact source. Completing a full six-max, raked, certified
strategy remains a separate source/accuracy milestone and cannot be inferred
from this exit result.
