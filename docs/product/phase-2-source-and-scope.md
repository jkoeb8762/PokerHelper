# Phase 2 Reference Pack: Source, Scope, and Limitations

**Status:** Approved implementation boundary
**Date:** 2026-11-18; reference-practice boundary amended 2026-11-19
**Roadmap checkpoint:** P2.1

## Source decision

The bundled reference pack is generated locally from the open-source
[`chirenonhive/poker-solver`](https://github.com/chirenonhive/poker-solver)
project at the immutable commit
`6d54d3725c50d5e74c8971723a616eb52d664f3c`.

The repository identifies its license as MIT and permits use, modification, and
redistribution subject to that license. PokerHelper records the upstream owner,
repository, commit, license URL, generation method, and hashes inside every
artifact. No commercial strategy site was scraped, reverse engineered, or
repackaged.

The pinned source is small and early-stage. Its repository maturity is not an
accuracy guarantee. PokerHelper therefore treats it as an inspectable generator
for the first Study pipeline, not as an authority equivalent to a mature
commercial solver.

## Reproducible configuration

The checked-in artifact was generated with:

| Input | Value |
|---|---:|
| Effective stack | 100 BB |
| SB / BB | 0.5 / 1 BB |
| Ante | 0 BB |
| Rake | none |
| Limp | enabled |
| Open raise-to | 2.5 BB |
| Later raise sizing | 100% pot after calling |
| Maximum raises | 4 |
| All-in option | enabled |
| Equity samples per canonical matchup | 8,000 |
| Equity seed | 1 |
| CFR+ iterations | 800 |
| IP realization factor | 1.00 |
| OOP realization factor | 0.85 |

The generator refuses a source checkout whose `HEAD` differs from the pinned
commit. Equity rows use deterministic seeds, and the generator validates its
completed artifact before publication.

## What the data means

The source solves an exact-combo heads-up preflop betting tree with blockers.
It reports a Nash-convergence measure for the game it defines. The Phase 2
solve reached `0.803 mbb/hand` exploitability inside that model.

When action closes with chips behind, however, the source does not solve a
postflop game. It awards the pot using a positional realized-equity heuristic.
The result is useful for exercising the artifact, navigation, blocker, and
study presentation systems, but it is only directional as a real 100 BB poker
strategy.

The source also omits rake. PokerHelper displays “No rake” for this pack rather
than silently showing the separately approved MVP rake preset.

## Product restrictions

This pack is:

- available only for offline Study and explicitly acknowledged reference-model
  practice;
- visibly labeled “approximate reference model” wherever strategy or feedback
  appears;
- limited to SB versus BB after four prior folds;
- not described as a complete six-max GTO solution;
- marked `trainerEligible: false` in immutable metadata;
- never presented as accuracy-certified grading;
- eligible for reproducible Phase 3 EV-loss scoring only after the user
  acknowledges that results are relative to this exact source model.

A later Trainer pack needs a new source decision and must model the intended
game, including rake and postflop continuation values, within the accuracy gate
in the golden-test contract before it may be described as certified.

## Generation command

After checking out the pinned upstream source, maintainers can run:

```powershell
python scripts/generate_phase2_artifact.py `
  --source-root <pinned-checkout> `
  --output-root backend/src/pokerhelper/resources/solutions `
  --equity-samples 8000 `
  --iterations 800 `
  --equity-workers 8 `
  --generated-at 2026-11-18T00:00:00-08:00
```

Generation creates a new content-addressed directory and refuses to overwrite
an existing version.
