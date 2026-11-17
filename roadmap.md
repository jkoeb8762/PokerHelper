# PokerHelper Product Roadmap

**Document status:** Active  
**Last updated:** 2026-11-17  
**Current stage:** Stage 1 — Product and Technical Foundation  
**Current phase:** Phase 1 — Poker Rules and Range Engine

## Purpose

PokerHelper is an offline poker study application for learning strategies that approximate game-theory-optimal play. Its core study loop is:

> Choose a situation → make a decision → compare it with a verified strategy → understand the mistake → drill related decisions → track improvement.

This roadmap is the project's source of truth for sequence, scope, dependencies, and completion criteria. A phase is complete only when every required exit checkpoint is satisfied.

## Status legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[!]` Blocked; the blocker must be documented next to the item
- **Deferred** means intentionally outside the current committed scope

## Product principles and guardrails

1. **Correctness before breadth.** Incorrect strategy, pot, range, or EV data is worse than missing data.
2. **One narrow vertical slice at a time.** Each phase must produce something demonstrable and useful.
3. **Every answer carries its assumptions.** Format, positions, stacks, blinds, antes, rake, ranges, bet tree, solver version, and accuracy metadata must be visible or inspectable.
4. **Solutions are reproducible and versioned.** Updating solution data must not silently change historical training results.
5. **Exact and approximate analysis are never conflated.** Out-of-tree or nearest-solution mappings must be labeled clearly.
6. **Study use only.** PokerHelper will not read a live poker table, provide advice during an active hand, automate an action, or function as real-time assistance.
7. **Use only authorized data.** Solver outputs and imported hand histories must be generated, licensed, or owned by the user; commercial strategy data will not be scraped or redistributed.

## Agreed first-release scope

| Dimension | Committed scope |
|---|---|
| Game | No-Limit Texas Hold'em |
| Format | Six-max cash |
| Stack depth | 100 BB |
| Rake | One documented preset |
| Coverage | Preflop |
| Decisions | Heads-up decisions within a six-max hand |
| Platform | Desktop-responsive web application |
| Solution model | Precomputed, immutable, and versioned |
| Usage | Post-session study and training only |

The first usable milestone is the **Six-Max 100 BB Preflop Trainer**. Tournaments, postflop coverage, hand-history analysis, and custom solving follow only after that milestone is trustworthy.

## Master roadmap

| Stage | Phase | Primary outcome | Status | Depends on |
|---|---|---|---|---|
| 1. Foundation | 0. Product definition and architecture | Scope, contracts, UX, and technical direction are explicit | Complete | — |
| 1. Foundation | 1. Poker rules and range engine | A tested, deterministic poker domain core | In progress | Phase 0 |
| 2. Preflop MVP | 2. Solution pipeline and study browser | Users can inspect validated preflop solutions | Not started | Phase 1 |
| 2. Preflop MVP | 3. Preflop trainer | Users can drill decisions and track EV-based results | Not started | Phase 2 |
| 3. Postflop and Analysis | 4. Restricted postflop study | Users can explore a deliberately limited postflop library | Not started | Phase 3 |
| 3. Postflop and Analysis | 5. Hand-history analyzer | Users can turn their own played hands into leak reports and drills | Not started | Phase 4 |
| 4. Tournaments | 6. Tournament chip-EV | Short-stack, ante, push/fold, and reshove study | Not started | Phase 3; portions of Phase 4 |
| 4. Tournaments | 7. ICM | Validated final-table tournament strategy support | Not started | Phase 6 |
| 5. Solver Platform | 8. Solver research and productionization | Validated custom and eventually on-demand solving | Not started | Phases 1–4 |

---

## Stage 1 — Product and Technical Foundation

### Phase 0 — Product Definition and Architecture

**Objective:** Remove ambiguity before implementation begins.

**Deliverables**

- Product charter and target-user definition
- Domain glossary
- MVP user journeys and low-fidelity wireframes
- Canonical `GameConfig`, `GameState`, `Action`, `Range`, `Strategy`, and `Solution` contracts
- Initial architecture decision record
- Testing and validation strategy
- Data provenance and real-time-assistance guardrail policy
- Prioritized implementation backlog

**Checkpoints**

- [x] P0.1 Agree on the first-release product scope.
- [x] P0.2 Establish the staged roadmap and phase order.
- [x] P0.3 Define the primary user persona and the exact MVP study journey. ([Evidence](docs/product/persona-and-mvp-study-journey.md))
- [x] P0.4 Approve poker terminology and units, including BB, chips, percentages, frequencies, and EV. ([Evidence](docs/product/terminology-and-units.md))
- [x] P0.5 Specify the canonical game-state and solution-data contracts. ([Evidence](docs/superpowers/specs/2026-08-17-canonical-contracts-design.md))
- [x] P0.6 Decide the initial technology stack and deployment model. ([Evidence](docs/superpowers/specs/2026-11-17-technology-stack-and-deployment-design.md))
- [x] P0.7 Create low-fidelity screens for scenario selection, study view, trainer, feedback, and session review. ([Evidence](docs/product/mvp-low-fidelity-wireframes.md))
- [x] P0.8 Define the golden-test corpus and accuracy expectations. ([Evidence](docs/product/golden-test-corpus-and-accuracy.md))
- [x] P0.9 Convert Phase 1 into sequenced, estimable implementation issues. ([Evidence](docs/plans/phase-1-implementation-backlog.md))
- [x] P0.10 Record the offline-study, data-rights, and privacy guardrails in the product requirements. ([Evidence](docs/product/offline-study-data-rights-and-privacy.md))

**Exit gate:** No unresolved product or architecture decision blocks the poker engine. The MVP journey can be explained from scenario selection through saved training result using the approved contracts and wireframes.

### Phase 1 — Poker Rules and Range Engine

**Objective:** Build a deterministic and thoroughly tested domain foundation.

**Deliverables**

- Cards, ranks, suits, deck, and board model
- Trusted hand-evaluation integration or implementation
- Six-max seats and position model
- Blinds, stacks, pot, betting-round, action, minimum-raise, and all-in logic
- Legal-action validation
- Cash-game rake model for the agreed preset
- 1,326-combination and 169-class preflop range representation
- Weighted ranges and card-removal support
- Canonical state serialization and stable identifiers
- Golden, unit, property, and regression tests

**Checkpoints**

- [x] P1.1 Cards, decks, and boards reject duplicates and impossible states. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.2 Hand evaluation matches the trusted reference test corpus. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.3 Six-max positions and action order are correct for every supported preflop state. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.4 Pot, stack, blind, raise, all-in, and legal-action calculations pass golden tests. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.5 The agreed rake preset is specified, implemented, and covered by boundary tests. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.6 All 1,326 combinations map correctly to the 169 preflop classes. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.7 Weighted-range operations preserve normalized weights and apply card removal correctly. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.8 Equivalent states serialize identically and receive stable identifiers. ([Evidence](docs/evidence/phase-1-verification.md))
- [x] P1.9 Invalid or unsupported states fail explicitly rather than being silently corrected. ([Evidence](docs/evidence/phase-1-verification.md))
- [!] P1.10 Continuous integration runs the complete deterministic test suite successfully. ([Workflow](.github/workflows/domain-ci.yml); [local evidence](docs/evidence/phase-1-verification.md)) **Blocker:** the repository has no GitHub remote/runner, so the configured Windows/Linux × Python 3.12/3.14 hosted matrix cannot be observed until the project is connected.

**Exit gate:** The engine can replay every supported six-max 100 BB preflop sequence, report legal actions and exact pot/stacks, and reproduce the same canonical state every time with all tests passing.

---

## Stage 2 — Six-Max 100 BB Preflop MVP

### Phase 2 — Solution Pipeline and Study Browser

**Objective:** Import, validate, store, and display trustworthy preflop strategies.

**Deliverables**

- Versioned solution-artifact specification
- Legally sourced preflop solution dataset
- Import, validation, and publication pipeline
- Immutable solution versions and provenance metadata
- Preflop action-tree navigation
- 13×13 range matrix
- Per-hand action frequencies and EVs
- Visible game and solver assumptions
- Bookmarkable study scenarios

**Checkpoints**

- [ ] P2.1 Select and document the authorized source and generation method for MVP solutions.
- [ ] P2.2 Define artifact metadata, including configuration, tree, solver, accuracy, source, and version.
- [ ] P2.3 Reject malformed solutions, impossible combos, invalid actions, and non-normalized frequencies.
- [ ] P2.4 Importing the same artifact is deterministic and does not create conflicting versions.
- [ ] P2.5 Users can navigate all supported opening, calling, and raising branches.
- [ ] P2.6 The range matrix displays fold, call, and raise mixes accurately for every supported hand.
- [ ] P2.7 A selected combo exposes action frequencies and EVs without losing suit-specific information.
- [ ] P2.8 The interface always exposes stack, positions, blinds, rake, action history, and solution version.
- [ ] P2.9 Representative nodes match the source solution within the documented numeric tolerance.
- [ ] P2.10 Common study nodes load within the agreed performance budget.

**Exit gate:** A user can select and navigate any scenario in the agreed preflop tree, inspect its complete strategy, and reproduce the displayed values from a validated, immutable source artifact.

### Phase 3 — Preflop Trainer

**Objective:** Complete the first useful product by turning solutions into repeatable practice.

**Deliverables**

- Scenario and position selection
- Range-weighted hand dealing
- Fold, call, and supported raise inputs
- Immediate and delayed feedback modes
- EV-loss scoring
- Mixed-frequency calibration metrics
- Optional random-number aid for mixed strategies
- Training sessions, decision history, and replay
- Results grouped by position, action sequence, and scenario
- Close-decision and mistake-review drills

**Checkpoints**

- [ ] P3.1 The trainer samples only possible hands at the correct solution weights.
- [ ] P3.2 User actions pass through the same legal-action engine used by Study mode.
- [ ] P3.3 Per-decision EV loss is calculated as `EV(best action) - EV(chosen action)` in documented units.
- [ ] P3.4 Low-frequency but supported actions are distinguished from strategically costly mistakes.
- [ ] P3.5 Feedback shows the reference mix, action EVs, assumptions, and a concise interpretation.
- [ ] P3.6 Sessions store the exact solution version needed to reproduce every result.
- [ ] P3.7 Users can review, filter, and replay previous decisions.
- [ ] P3.8 Users can launch a targeted drill from prior mistakes.
- [ ] P3.9 Statistics correctly aggregate volume, EV loss, and frequency calibration.
- [ ] P3.10 End-to-end usability tests cover scenario selection through session review.

**Exit gate — MVP release:** A user can choose a supported six-max 100 BB preflop situation, make decisions, receive reproducible EV-based feedback, review the session, and drill identified weaknesses. Poker-domain and solution validation tests pass with no unresolved critical defects.

---

## Stage 3 — Restricted Postflop and Hand Analysis

### Phase 4 — Restricted Postflop Study

**Objective:** Add postflop learning without pretending to cover the full no-limit game tree.

**Initial boundary:** Heads-up pots, a small documented set of preflop formations, stack/rake presets, representative boards, and constrained bet trees.

**Deliverables**

- Suit-aware postflop combo ranges and card removal
- Flop, turn, and river state navigation
- Restricted postflop solution pipeline
- Board and texture filters
- Range strategy, equity, EV, and action-frequency views
- Hand-category and blocker inspection
- Clear unsupported/out-of-tree states

**Checkpoints**

- [ ] P4.1 Approve the first formations, boards, runouts, and bet-size trees.
- [ ] P4.2 Postflop ranges remove all board and known hole cards correctly.
- [ ] P4.3 Every node maintains correct pot, stacks, actor, board, and legal actions.
- [ ] P4.4 Strategy, equity, and EV values match the source on a representative validation pack.
- [ ] P4.5 Users can filter strategically relevant board and hand categories.
- [ ] P4.6 Suit-specific blocker differences remain inspectable.
- [ ] P4.7 Unsupported lines are explicit and never presented as exact solutions.
- [ ] P4.8 Large solution artifacts meet the agreed storage and load-time budgets.
- [ ] P4.9 Trainer support is added only for the validated postflop subset.
- [ ] P4.10 Product copy clearly communicates the limits of the restricted tree.

**Exit gate:** Users can accurately study and drill the approved postflop subset from flop through river, and the product clearly distinguishes supported from unsupported states.

### Phase 5 — Hand-History Analyzer

**Objective:** Convert a user's own played hands into reproducible reviews, leak reports, and drills.

**Deliverables**

- Parser for one approved hand-history format
- Canonical hand normalization and replay
- Site-format fixture corpus
- Solution matching and out-of-tree classification
- Decision-level EV-loss estimates
- Hand and session reports
- Leak aggregation and drill creation
- Import privacy, retention, and deletion controls

**Checkpoints**

- [ ] P5.1 Select the first supported hand-history format and collect authorized fixtures.
- [ ] P5.2 Valid hands round-trip from raw text through normalization and replay without state drift.
- [ ] P5.3 Malformed, partial, duplicate, and unsupported hands produce useful diagnostics.
- [ ] P5.4 Every analyzed decision is labeled `exact`, `abstracted`, `nearest available`, or `unsupported`.
- [ ] P5.5 The analyzer never silently snaps an action or sizing to a different tree.
- [ ] P5.6 EV-loss estimates retain the matched solution version and mapping explanation.
- [ ] P5.7 Reports identify leaks by position, action sequence, street, and supported board category.
- [ ] P5.8 Users can open a hand replay and start a drill from a supported mistake.
- [ ] P5.9 Imported data follows the approved privacy, retention, export, and deletion policy.
- [ ] P5.10 The complete fixture suite passes after every parser or engine change.

**Exit gate:** A user can import their own supported hand history, verify an accurate replay, understand the confidence and limitations of each comparison, identify leaks, and turn supported mistakes into drills.

---

## Stage 4 — Tournament Study

### Phase 6 — Tournament Chip-EV

**Objective:** Extend the trusted preflop experience to tournament structures before introducing payout pressure.

**Deliverables**

- Tournament configuration model
- Variable and asymmetric stack depths
- Antes and big-blind ante
- Short-stack preflop solution library
- Push/fold, raise/fold, call-off, and reshove study
- Tournament chip-EV trainer and reports

**Checkpoints**

- [ ] P6.1 Tournament configuration represents blinds, antes, seats, and individual stacks exactly.
- [ ] P6.2 Action legality and side-pot behavior pass asymmetric-stack and all-in tests.
- [ ] P6.3 Initial stack-depth and ante presets are approved and documented.
- [ ] P6.4 Push/fold, call-off, and reshove solutions pass source validation.
- [ ] P6.5 Study and trainer screens label all results explicitly as chip-EV.
- [ ] P6.6 Results remain reproducible across tournament configuration and solution versions.
- [ ] P6.7 Performance reports segment correctly by effective stack and tournament scenario.
- [ ] P6.8 Unsupported multiway or ICM states are not approximated as chip-EV without a warning.

**Exit gate:** Users can accurately study and drill the approved short-stack tournament scenarios under chip-EV assumptions, including antes and asymmetric stacks.

### Phase 7 — Independent Chip Model (ICM)

**Objective:** Support payout-sensitive final-table decisions with validated assumptions.

**Deliverables**

- Payout structure and remaining-field model
- ICM equity calculator
- Full remaining-stack distribution
- Preflop final-table solution library
- ICM risk-premium and EV views
- ICM study, training, and reporting

**Checkpoints**

- [ ] P7.1 ICM inputs require the full payout structure and all remaining player stacks.
- [ ] P7.2 ICM equity calculations match an independent reference corpus.
- [ ] P7.3 Chip-EV and monetary/tournament-equity units cannot be confused in the interface.
- [ ] P7.4 Initial final-table configurations and action trees are approved and documented.
- [ ] P7.5 Solution strategies and EVs pass independent validation.
- [ ] P7.6 Trainer feedback explains risk premium and payout pressure using reproducible values.
- [ ] P7.7 Changes to payouts or any player's stack generate distinct canonical scenarios.
- [ ] P7.8 Postflop ICM and PKO support remain deferred until separately scoped and validated.

**Exit gate:** Users can study and train on the approved preflop final-table configurations with independently validated ICM equities and unambiguous monetary/tournament-equity feedback.

---

## Stage 5 — Solver Research and Productionization

### Phase 8A — Algorithm Research on Toy Games

**Objective:** Prove solver correctness in games with known or independently verifiable equilibria.

**Checkpoints**

- [ ] P8A.1 Implement or integrate a common extensive-form game representation.
- [ ] P8A.2 Reproduce expected strategies for Kuhn poker.
- [ ] P8A.3 Reproduce expected strategies for Leduc poker.
- [ ] P8A.4 Track exploitability or another approved convergence measure.
- [ ] P8A.5 Test deterministic seeds, checkpoints, resume behavior, and numerical stability.
- [ ] P8A.6 Compare the implementation against an independent reference framework.

**Exit gate:** The research solver reliably converges on approved toy games and reports a meaningful, independently checked accuracy measure.

### Phase 8B — Restricted Hold'em Subgames

**Objective:** Advance from toy games to small, explicitly constrained no-limit Hold'em trees.

**Checkpoints**

- [ ] P8B.1 Define the first heads-up Hold'em subgame and its action abstraction.
- [ ] P8B.2 Add chance sampling and suit-isomorphism tests where appropriate.
- [ ] P8B.3 Measure memory, compute time, convergence, and artifact size.
- [ ] P8B.4 Compare outputs with trusted solutions across a representative node pack.
- [ ] P8B.5 Document all abstractions and their expected error sources.
- [ ] P8B.6 Demonstrate that generated artifacts can be consumed by the existing Study mode unchanged.

**Exit gate:** The solver generates a restricted Hold'em solution that meets a predeclared accuracy and resource budget and integrates through the standard solution contract.

### Phase 8C — Production Solve Pipeline

**Objective:** Make solving reproducible, observable, fault-tolerant, and safe to operate.

**Checkpoints**

- [ ] P8C.1 Create asynchronous solve jobs with validated configurations.
- [ ] P8C.2 Add progress, cancellation, checkpoint, retry, and failure reporting.
- [ ] P8C.3 Record code, configuration, seed, hardware, accuracy, and provenance for every solve.
- [ ] P8C.4 Enforce compute, memory, time, and storage quotas.
- [ ] P8C.5 Validate and publish completed artifacts through the standard solution pipeline.
- [ ] P8C.6 Establish monitoring for convergence, failures, queue time, cost, and artifact integrity.

**Exit gate:** Approved solve jobs can run asynchronously, recover from interruption, publish immutable validated artifacts, and be reproduced from recorded metadata.

### Phase 8D — Custom and On-Demand Solving

**Objective:** Allow users to configure supported trees without compromising accuracy or transparency.

**Checkpoints**

- [ ] P8D.1 Scope the supported configuration surface and hard resource limits.
- [ ] P8D.2 Validate user inputs before estimating solve cost or accepting a job.
- [ ] P8D.3 Present accuracy, abstraction, and convergence information with every result.
- [ ] P8D.4 Compare custom solutions against the validated reference pack.
- [ ] P8D.5 Add caching and deduplication for identical canonical solve requests.
- [ ] P8D.6 Complete load, abuse, privacy, and cost-control testing.

**Exit gate:** Users can request supported custom solutions, understand their assumptions and accuracy, and receive reproducible results within controlled operational limits.

---

## Cross-cutting release gates

Every user-facing release must satisfy the following:

- [ ] Domain calculations have unit and golden-test coverage.
- [ ] Relevant solution values pass source or independent validation.
- [ ] Strategy frequencies normalize within the documented tolerance.
- [ ] Impossible card combinations and states are rejected.
- [ ] Game, tree, data-source, solver, and accuracy assumptions are inspectable.
- [ ] Historical results retain enough version data to be reproduced.
- [ ] Unsupported or approximate results are labeled prominently.
- [ ] Accessibility, responsive-layout, and primary-flow usability checks pass.
- [ ] Privacy and data-retention behavior match the approved policy.
- [ ] No feature reads or responds to a live poker-table state.
- [ ] Known limitations and newly deferred work are documented.

## Success metrics

### Product metrics

- Users can complete the MVP journey without external instruction.
- Training volume and returning study sessions increase over time.
- EV loss decreases on held-out scenarios rather than only repeated hands.
- Users can correctly explain why a marked decision was costly.
- Analyzer users turn identified leaks into completed drills.

### Technical and trust metrics

- Zero unresolved critical poker-state or solution-correctness defects at release.
- One hundred percent of results identify their configuration and solution version.
- One hundred percent of analyzer decisions carry a match-quality label.
- Golden tests remain deterministic across supported platforms.
- Common study and trainer interactions remain within the agreed latency budget.

## Deferred capability backlog

These capabilities require their own future scope and checkpoints:

- Multiway postflop solving
- Progressive knockout and bounty tournament models
- Postflop ICM
- Population models and nodelocking
- Exploitative counterstrategy tools
- Arbitrary stack depths and bet trees
- Pot-Limit Omaha and other poker variants
- AI-generated strategic explanations
- Collaborative study and coaching tools
- Native mobile applications
- Billing and commercial subscription management

## Roadmap maintenance rules

1. Update the current stage and phase at the top whenever work advances.
2. Change a checkpoint to complete only when evidence exists in code, tests, documentation, or an approved artifact.
3. Record blocked items with the blocker and the decision or dependency required.
4. Add newly discovered work to the appropriate phase; do not silently expand the current phase.
5. Changes to committed scope require a dated decision in the log below.
6. At each phase exit, review all cross-cutting release gates and record the evidence.

## Decision log

| Date | Decision |
|---|---|
| 2026-08-16 | Begin with a six-max, 100 BB, preflop NLHE cash-game study and training product. |
| 2026-08-16 | Use precomputed, versioned solutions before attempting a production solver. |
| 2026-08-16 | Sequence development as foundation → preflop MVP → restricted postflop → analyzer → tournaments → solver platform. |
| 2026-08-16 | Keep PokerHelper strictly offline-study oriented and prohibit real-time assistance features. |
| 2026-08-16 | Target an improving recreational or intermediate six-max cash player and adopt the approved eight-step MVP study journey. |
| 2026-08-16 | Use grouped hand classes for range study, but require exact rank-and-suit combos for every dealt or reviewed Trainer hand. |
| 2026-08-17 | Adopt layered, technology-neutral canonical contracts with replay-derived state, exact-combo strategy data, immutable solution nodes, and auditable Trainer snapshots. |
| 2026-11-17 | Use a local-only Python/FastAPI and React/Vite modular monolith with SQLite and immutable local solution files; defer accounts and hosting. |
| 2026-11-17 | Adopt a source-backed golden corpus, exact-decimal accuracy contract, and explicit MVP feedback thresholds. |
| 2026-11-17 | Treat the no-real-time-assistance, authorized-data, and local-privacy boundaries as enforceable product requirements. |
| 2026-11-17 | Adopt the project-owned `MVP_CASH_5PCT_1BB_NFND_V1` rake preset: 5%, 1 BB cap, no-flop-no-drop, centi-BB rounding down. |
| 2026-11-17 | Keep the Phase 1 poker domain standard-library-only and Python 3.12-compatible while retaining Python 3.14 as the primary release toolchain. |

## Change log

| Date | Change |
|---|---|
| 2026-08-16 | Created the initial roadmap and marked Phase 0 as in progress. |
| 2026-08-16 | Documented the primary user persona and MVP study journey; completed P0.3. |
| 2026-08-16 | Drafted the controlled poker terminology and unit conventions; P0.4 is in progress pending review. |
| 2026-08-16 | Incorporated exact dealt-card notation, approved the terminology and unit conventions, and completed P0.4. |
| 2026-08-17 | Drafted the canonical game-state, solution-data, Study, and Trainer contracts; P0.5 is pending final written-spec review. |
| 2026-08-17 | Approved the canonical contract specification and completed P0.5. |
| 2026-11-17 | Approved the technology design, low-fidelity MVP screens, accuracy contract, Phase 1 backlog, and guardrail requirements; completed Phase 0 and opened Phase 1. |
| 2026-11-17 | Implemented and locally verified P1.1–P1.9 with 55 deterministic tests; configured the P1.10 CI matrix, pending its first connected hosted run. |
