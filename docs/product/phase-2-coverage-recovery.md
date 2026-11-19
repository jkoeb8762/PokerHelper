# Phase 2 Coverage Recovery and Open-Source Solver Audit

**Status:** Active — Phase 2 reopened  
**Date:** 2026-11-19  
**Roadmap checkpoints:** P2.1 and P2.11–P2.18

## Why Phase 2 was reopened

The approved first release is a six-max, 100 BB preflop cash-game study and
training product. The approved journey and wireframes include position and
action-sequence selection across the six-max table; `BB vs CO open` is the
canonical example.

The implementation instead bundled one 18-node tree covering only SB versus BB
after UTG, HJ, CO, and BTN fold. That pack correctly exercised the solution
pipeline, Study browser, and Trainer mechanics, but it did not replace the
approved coverage. Phase 2 and the Phase 3 release gate were therefore marked
complete prematurely.

The existing `phase2-hu-sb-bb-100bb-v1.1` artifact remains an immutable
reference fixture. It is not the MVP solution library.

## Complete-data qualification gates

A source is not complete merely because it displays six-max charts. Before it
can close Phase 2 it must provide or reproducibly generate:

1. every position and action sequence in the approved P2.11 coverage matrix;
2. the 100 BB six-max game configuration and the project-owned
   `MVP_CASH_5PCT_1BB_NFND_V1` rake policy;
3. a declared preflop betting tree, including sizes, calls, re-raises, all-ins,
   and every deliberately excluded branch;
4. normalized action frequencies and reach weights at every supported node;
5. action-conditioned EVs in BB, not only a preferred action or chart color;
6. enough convergence, uncertainty, and model-accuracy evidence to label the
   result honestly;
7. deterministic configuration, seeds, source revision, and hashes;
8. a license and provenance chain that permit use and redistribution; and
9. export into PokerHelper's immutable solution-artifact contract.

Grouped 169-class preflop output may be expanded to exact dealt combos when
suit symmetry is valid, but exact rank-and-suit combos remain the Trainer and
history representation.

## Candidate audit

| Candidate | Reuse status | Useful strengths | Blocking gaps for the MVP |
|---|---|---|---|
| [`chirenonhive/poker-solver`](https://github.com/chirenonhive/poker-solver) | MIT; already pinned for the reference fixture | Exact blockers and auditable heads-up CFR+ output | SB/BB heads-up only; no rake; approximate deep-stack postflop realization |
| [`wesboyt/donksolver`](https://github.com/wesboyt/donksolver) 0.1.0 | MIT; strongest integration candidate so far | Up to six players, 169 preflop classes, no-limit betting semantics, rake, versioned policies, Windows wheels, deterministic abstractions, and extensive audits | Ships no solved and measured six-max blueprint; explicitly provides no six-max Nash certificate; normal presets replace multiway postflop with check-down values; no exported per-action EV table; full multiway solve is much larger |
| [`jamatten/DCFR-SOLVER-nodelocking-GUI`](https://github.com/jamatten/DCFR-SOLVER-nodelocking-GUI) | MIT; possible component and benchmark source | Six-player 100 BB MCCFR tree, configurable preflop sizes, 169 classes, deterministic seed, and chart extraction | No rake; preflop closing actions use sampled-board/check-down values plus a positional adjustment; exports probabilities rather than action EVs; no independent six-max accuracy certificate |
| [`MKovNEU/Poker-Solver-v3`](https://github.com/MKovNEU/Poker-Solver-v3) | **Not reusable unless the author adds a license** | Fast 2–6 player preflop tree, configurable sizes, and postflop handoff | Public code has no license; multiway calls to a flop are omitted; opponents are approximated as independent in 3+ player states; heuristic flop realization; no documented rake |
| [`jensbaagaard/poker-practice`](https://github.com/jensbaagaard/poker-practice) range data | Repository states MIT/free-to-use | Broad 100 BB position and action-frequency coverage in a compact chart format | No action EVs; no solver revision, solve configuration, convergence record, or independent accuracy bound for the data; no documented rake model; therefore not an authoritative grading source |
| [`zwarag/gto-open`](https://github.com/zwarag/gto-open) | Public planning repository | Describes the same need for an open, versioned preflop database | Contains a plan, not a generated dataset |

### Audit conclusion

No audited candidate currently supplies a drop-in, licensed, complete dataset
meeting PokerHelper's frequencies, EV, rake, provenance, and accuracy gates.
Open-source implementation is nevertheless feasible enough to continue as a
controlled research spike. `donksolver` is the leading base because it is
licensed, runnable on Windows, supports six players and rake, and exposes a
testable game engine. It is not approved as the final source yet.

## Local feasibility spike

All spike files are ignored and stored under
`E:\PokerHelper\.cache\solver-evaluation`; nothing was placed on `C:` by the
project.

| Measurement | Result |
|---|---:|
| Available logical processors reported to the process | 20 |
| Free space on `E:` before the spike | 895.4 GB |
| Deterministic 169/50/50/50 abstraction build | 11.4 seconds; 23.21 MiB |
| `6max-lite`, 100 BB tree | 1,111,798 nodes; 103,517,457 table entries |
| `6max-lite` float tables | 0.77 GB |
| `6max` float tables | 1.26 GB |
| `6max-mw` float tables | 8.96 GB |
| 100,000-iteration `6max-lite` pilot | about 30 seconds; roughly 2.6k–4.2k iterations/second |

The pilot proves that tree construction and a research solve are locally
possible. It does **not** prove convergence or strategy quality: the reported
root-EV standard errors remained hundreds of solver chips at 100,000
iterations. At the observed rate, the project's documented 50-million-iteration
example would take several hours, and multiway tables would require materially
more memory. A longer multi-seed run and policy-stability analysis are required
before adoption.

## How licensed components may be combined

PokerHelper may integrate compatible open-source code, but will not combine
strategies by averaging their frequencies. An average of independently
approximated strategies is not automatically an equilibrium, and EVs from one
game model do not remain valid after mixing them with another.

The proposed project-owned pipeline is component-based:

1. **Game and payoff layer:** six-max action order, stacks, legal actions, side
   pots, and the approved rake policy, replay-checked against PokerHelper's
   canonical domain engine.
2. **Solving layer:** one pinned MCCFR/LCFR/DCFR implementation with deterministic
   seeds and restartable checkpoints. Other licensed solvers are independent
   comparisons, not blended policies.
3. **Continuation-value layer:** declared postflop values for every preflop
   terminal. Heads-up continuations may be estimated with a separately pinned
   open-source postflop solver. Multiway continuations must be solved,
   explicitly excluded by the approved coverage matrix, or visibly identified
   as an approximation; they cannot silently become check-down poker.
4. **Value-export layer:** reach, action frequency, and action-conditioned EV for
   each supported preflop information set, including sampling uncertainty where
   values are estimated.
5. **Validation layer:** toy-game convergence, rule/payoff differential tests,
   multiple seeds, policy-stability measurements, independent spot comparisons,
   normalization, and fail-closed artifact validation.
6. **Publication layer:** content-addressed PokerHelper artifacts containing the
   exact source revisions, configuration, seeds, resource measurements,
   limitations, and hashes.

Only code and data with compatible, recorded licenses may enter this pipeline.
A public repository with no license is treated as all-rights-reserved. Public
commercial outputs, screenshots, and APIs will not be scraped. When a repository
contains data whose provenance is weaker than its code license, that data may be
used only as a non-authoritative comparison until its rights and generation
record are established.

## Recovery sequence

1. Approve P2.11's exact scenario matrix and clarify how the MVP treats cold
   calls, squeezes, and other paths that could reach a multiway flop.
2. Extend the feasibility spike to multiple seeds and a meaningful iteration
   budget; measure policy stability, not merely runtime.
3. Prototype action-conditioned EV export and verify the EV baseline against
   PokerHelper's current heads-up fixture and independent toy games.
4. Decide whether the resulting approximation meets the product's honesty and
   learning-quality threshold. If it does not, stop and choose an externally
   generated/licensed dataset rather than lowering the gate silently.
5. Generate, validate, and publish the complete immutable pack; then generalize
   the SB/BB-only UI controls and re-run the Phase 2 and Phase 3 exit journeys.

## Decision status

- The SB-versus-BB artifact is retained only as a reference and regression
  fixture.
- Phase 2 is reopened; Phase 3 mechanics remain implemented but its MVP release
  gate is blocked.
- No final solver source has been approved.
- A project-owned solver assembled from compatible licensed components is the
  preferred fallback if no qualifying complete open dataset is found.
