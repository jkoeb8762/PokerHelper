# Canonical Game-State and Solution-Data Contracts

**Status:** Approved  
**Date:** 2026-08-17  
**Approved:** 2026-08-17  
**Roadmap checkpoint:** P0.5  
**Scope:** Technology-neutral contracts for the six-max, 100 BB, preflop NLHE cash MVP

## Purpose

This specification defines PokerHelper's canonical domain contracts: the single validated representation used by the poker engine, solution library, Study experience, Trainer, and historical review. It intentionally does not choose a programming language, database, API framework, or physical storage layout; those decisions belong to P0.6.

JSON fragments in this document are illustrative serializations of the contracts. They are not final JSON Schema. Decimal values have exact decimal semantics even when shown as JSON numbers. The selected implementation must not use ordinary binary floating-point values as the source of truth for poker amounts, probabilities, or EV.

## Approved design decisions

1. Use a layered canonical contract suite rather than flat documents or full event sourcing for the MVP.
2. Keep the contracts technology-neutral and include illustrative JSON examples.
3. Cover poker and solution contracts plus the minimum Trainer records required for reproducible history.
4. Represent stacks, pots, wagers, and EV as exact decimal BB values.
5. Use all 1,326 exact combos canonically; derive the 169 grouped hand classes for Study views.
6. Treat `GameConfig` plus ordered action history as authoritative; `GameState` is derived.
7. Use content-based IDs for immutable definitions and generated IDs for user activity.
8. Organize a solution as an immutable manifest with independently addressable tree nodes.
9. Store references plus a compact feedback snapshot in each completed Trainer decision.
10. Admit data to the canonical model only through explicit normalization and strict validation.
11. Preserve `ALL_IN` as a user/solution option while resolving it to its underlying call, bet, or raise.
12. Store exact resolved action amounts; derive BB, pot-percentage, and small/large descriptions for display.

## Goals

- Reproduce every supported state from its game configuration and ordered actions.
- Make poker calculations, solution values, and Trainer feedback independently testable.
- Preserve exact suits from computation through Trainer history and replay.
- Prevent display wording, cached values, or imported text from becoming authoritative.
- Deduplicate identical immutable content while tracking separate training activity.
- Keep historical results understandable and recalculable if solution data is archived.
- Preserve a clean migration path toward event sourcing without building that complexity now.

## Non-goals

- Selecting a language, database, framework, or deployment topology
- Defining physical table layouts, indexes, compression, or API routes
- Defining accounts, authentication, cloud synchronization, or user profiles
- Defining hand-history import formats
- Defining postflop board, equity, ICM, tournament, or solver-research contracts
- Choosing the production MVP rake preset or solution source
- Setting numerical solver tolerances, feedback thresholds, or minimum frequency samples; P0.8 owns those values

## Contract architecture

The contracts form four layers:

| Layer | Primary contracts | Responsibility |
|---|---|---|
| Poker domain | `GameConfig`, `ResolvedAction`, `GameState` | Define rules and reproduce a legal poker state |
| Strategy | `Range`, `ActionOption`, `Strategy`, `SolutionManifest`, `SolutionNode` | Represent exact-combo ranges, actions, frequencies, EVs, and the solution tree |
| Study | `Scenario` | Identify a supported public decision point |
| Trainer | `DecisionResult`, `TrainingSession` | Preserve what the user saw, chose, and was told |

Dependencies flow in one direction:

```text
Trainer → Study → Strategy → Poker domain
```

The poker domain has no knowledge of solutions, sessions, or users. The strategy layer consumes poker-domain states. Study points to validated strategy content. Trainer consumes all three lower layers but does not redefine them.

## Common conventions

### Schema versions

Every top-level record carries a `schemaVersion`. Unsupported major versions are rejected rather than interpreted heuristically.

### Identity profiles

Deterministic records also carry an `identityProfileVersion`. Identity calculation uses a canonical semantic payload rather than raw serialized bytes. It:

- normalizes exact decimals and card notation;
- preserves ordered collections such as action history;
- sorts unordered collections such as combo entries;
- includes every behaviorally meaningful field;
- excludes the record's own ID, generated timestamps, display labels, cached state, and descriptive metadata; and
- emits a typed content hash such as `game:<hash>`, `node:<hash>`, or `scenario:<hash>`.

Separating the identity profile from the schema version allows a non-semantic schema migration without unnecessarily changing content identity.

Example hashes in this document are shortened for readability; production identities use the complete digest selected in P0.6.

### Generated identities

`DecisionResult` and `TrainingSession` use opaque generated IDs. Two identical training decisions completed at different times are separate user events.

### Exact decimals

Canonical decimal values normalize before comparison and hashing. For example, `2.5`, `2.50`, and `02.500` have the same semantic value. Negative zero normalizes to zero. Display rounding never mutates canonical values.

The concrete fixed-point or decimal type is selected in P0.6. Implementations must support at least the source precision of imported solution values and the precision required by P0.8.

### Timestamps

User-activity timestamps use UTC instants in ISO 8601 form. Local time is a presentation concern. Generated timestamps do not affect deterministic content identities.

### Extensions

Known core fields are strict. Optional future data must live in a namespaced `extensions` object. An extension cannot alter poker behavior, strategy interpretation, identity, or scoring unless promoted into a future core schema version.

## Poker-domain contracts

### `GameConfig`

`GameConfig` defines the rules and starting conditions for a game tree.

Required semantic fields:

| Field | Meaning |
|---|---|
| `schemaVersion` | Contract version |
| `identityProfileVersion` | Canonical identity algorithm version |
| `gameConfigId` | Deterministic content ID |
| `variant` | `NLHE` for the MVP |
| `bettingStructure` | `NO_LIMIT` for the MVP |
| `gameType` | `CASH` for the MVP |
| `tableSize` | `6` for six-max |
| `positions` | Ordered six-max positions and starting stacks |
| `smallBlindBb` | Exact small-blind amount in BB |
| `bigBlindBb` | Exact big-blind amount; `1` by definition in normalized display units |
| `anteBb` | Exact per-player ante; `0` for the MVP |
| `rakePolicy` | Complete, versioned cash-game rake rules |

Illustrative structure:

```json
{
  "schemaVersion": "1.0.0",
  "identityProfileVersion": "1",
  "gameConfigId": "game:sha256:7f3a91c2",
  "variant": "NLHE",
  "bettingStructure": "NO_LIMIT",
  "gameType": "CASH",
  "tableSize": 6,
  "positions": [
    { "position": "UTG", "startingStackBb": 100 },
    { "position": "HJ",  "startingStackBb": 100 },
    { "position": "CO",  "startingStackBb": 100 },
    { "position": "BTN", "startingStackBb": 100 },
    { "position": "SB",  "startingStackBb": 100 },
    { "position": "BB",  "startingStackBb": 100 }
  ],
  "smallBlindBb": 0.5,
  "bigBlindBb": 1,
  "anteBb": 0,
  "rakePolicy": {
    "policyVersion": "1",
    "rate": 0.05,
    "capBb": 1,
    "noFlopNoDrop": true,
    "collectionRule": "QUALIFYING_POSTFLOP_POT"
  }
}
```

The rake values above demonstrate contract shape only. The production preset is selected and validated before solution generation.

Starting stacks are measured before forced bets. The engine applies blinds and future antes from `GameConfig`; forced contributions are not duplicated as player decisions.

### `ResolvedAction`

An ordered action history contains resolved poker actions. The MVP action types are:

- `FOLD`
- `CHECK`
- `CALL`
- `RAISE_TO`

`BET_TO` is reserved for future postflop use. Preflop voluntary aggression is a raise because the big blind is the existing wager.

Required fields by action type:

| Type | Required semantic fields |
|---|---|
| `FOLD` | `actor`, `type` |
| `CHECK` | `actor`, `type` |
| `CALL` | `actor`, `type` |
| `BET_TO` | `actor`, `type`, `targetBb` |
| `RAISE_TO` | `actor`, `type`, `targetBb` |

Call amounts are derived from state and are not duplicated. `targetBb` means the player's total current-street contribution after the bet or raise, never an additional amount.

Resolved actions also expose deterministic annotations:

- `isAllIn`: whether the action consumes the actor's entire stack behind;
- `raiseClassification`: `FULL_RAISE` or `SHORT_RAISE`, required only for a resolved raise.

These annotations are recalculated during replay. They are convenient for querying and future features but are not independent authorities.

Action order is represented once by array position in the enclosing action history. A separate action-level sequence field is deliberately omitted.

Example:

```json
{
  "actor": "BB",
  "type": "RAISE_TO",
  "targetBb": 100,
  "isAllIn": true,
  "raiseClassification": "FULL_RAISE"
}
```

### All-in input versus resolved action

`ALL_IN` is a valid user-facing and solution-tree input kind, not an underlying poker action type. It resolves according to state:

| Situation | Resolved type |
|---|---|
| Facing a wager that covers the remaining stack | `CALL` with `isAllIn: true` |
| No wager postflop | `BET_TO` with `isAllIn: true` |
| Able to increase the wager | `RAISE_TO` with `isAllIn: true` and raise classification |

This distinction preserves the user's all-in selection while retaining correct call, bet, raise, minimum-raise, and reopening semantics.

### `GameState`

`GameState` is derived by applying `GameConfig` and replaying the ordered `ResolvedAction` history.

It exposes:

- current street;
- next player to act;
- current pot;
- current wager level;
- amount to call;
- minimum legal full-raise target;
- last full-raise increment;
- stack behind, current-street contribution, total contribution, and status for each player;
- legal poker actions;
- whether the betting round is closed; and
- whether the hand itself is terminal.

Player status is `ACTIVE`, `FOLDED`, or `ALL_IN`.

A state may include a deterministic `stateId` based on its game configuration and ordered actions. A cached state snapshot may be stored or transmitted for performance, but configuration and action history remain authoritative. If replay disagrees with the snapshot, validation fails.

### Poker-state invariants

- Positions are unique and match the configured table.
- Stacks, pots, contributions, calls, and wagers are never negative.
- Forced bets do not exceed the corresponding starting stack.
- Only the expected player acts.
- A player never contributes more than their stack.
- Fold, check, call, bet, and raise legality follows no-limit rules.
- Short all-in raises are distinguished from full raises and do not incorrectly reopen betting.
- Pot and stack changes reconcile exactly.
- Folded and all-in players do not take later voluntary actions.
- A player with no stack behind is marked all-in.
- Replaying identical configuration and actions always produces the same state.

Legal poker actions come from the poker engine. Solution-supported options are a separate strategy-layer concern.

## Strategy contracts

### Exact combo notation

Canonical strategy computation uses exact combos such as `KsKd`, `AsKs`, and `AhKc`. Non-paired combos list the higher rank first. Pairs use stable suit order `s`, `h`, `d`, `c`.

Grouped classes such as `KK`, `AKs`, and `AKo` are derived presentation and aggregation views. They never replace the underlying exact combos.

### `Range`

A range is a sparse collection of exact combo reach weights:

```text
exact combo → reach weight in [0, 1]
```

Range weights describe how much of a combo reaches the node. They are not required to sum to `1`. A combo absent from the sparse collection has weight zero. Sampling or range-level reporting may derive a normalized distribution from positive weights.

Illustrative structure:

```json
{
  "entries": [
    { "combo": "AsKs", "weight": 1 },
    { "combo": "AhKh", "weight": 1 },
    { "combo": "AdKd", "weight": 0.5 }
  ]
}
```

Range entries are unique, canonically sorted, and checked against all known cards. No impossible combo may enter a canonical range.

### `ActionOption`

A solution node declares the options supported for its acting player. An option includes:

- stable node-local `optionId`;
- user-input kind: `FOLD`, `CHECK`, `CALL`, `BET`, `RAISE`, or `ALL_IN`;
- exact `resolvedAction` for that node; and
- deterministic display order.

Example fixed raise:

```json
{
  "optionId": "raise_11",
  "inputKind": "RAISE",
  "resolvedAction": {
    "actor": "BB",
    "type": "RAISE_TO",
    "targetBb": 11,
    "isAllIn": false,
    "raiseClassification": "FULL_RAISE"
  },
  "displayOrder": 3
}
```

Example all-in option:

```json
{
  "optionId": "all_in",
  "inputKind": "ALL_IN",
  "resolvedAction": {
    "actor": "BB",
    "type": "RAISE_TO",
    "targetBb": 100,
    "isAllIn": true,
    "raiseClassification": "FULL_RAISE"
  },
  "displayOrder": 4
}
```

A node cannot contain two options that resolve to the same canonical poker action.

Action options do not store `SMALL`, `LARGE`, or pot-percentage descriptions. Presentation derives those labels from the state, exact target, and other actions available at the node. The solution manifest retains the solver's original sizing configuration as provenance when available.

### `Strategy`

The acting player's strategy contains an entry for every exact combo with positive acting-range weight. Each entry records one result per supported option:

- unrounded reference frequency; and
- decision-point action EV in BB.

Illustrative structure:

```json
{
  "combo": "As5s",
  "options": [
    { "optionId": "fold", "frequency": 0.025, "actionEvBb": 0 },
    { "optionId": "call", "frequency": 0.55, "actionEvBb": 0.179 },
    { "optionId": "raise_11", "frequency": 0.425, "actionEvBb": 0.184 }
  ]
}
```

Frequencies for one combo cover every supported option and sum to `1` within the P0.8 tolerance. Action EV must exist for every option used in grading, including zero-frequency options.

Range-level action frequency is derived by weighting combo frequencies by their reach weights. It is not stored as an independent authority.

The product normalizes imported EV to the approved decision-point baseline: chips committed before the decision are sunk and folding has EV `0 BB`. The source baseline and normalization method remain in provenance.

### `SolutionManifest`

One immutable manifest describes one complete solution artifact. It includes:

- schema, identity profile, and solution IDs;
- referenced game configuration;
- root node;
- node index and integrity hashes;
- source and authorization provenance;
- generator or solver name and version;
- complete generation configuration, including original sizing rules;
- source and normalized EV baselines;
- accuracy and convergence metadata supplied by the source;
- creation instant;
- supported scope; and
- documented limitations.

Publication status is operational metadata rather than strategy content. Only validated, published solutions may drive Study or Trainer.

### `SolutionNode`

Each independently addressable tree node includes:

- deterministic node and solution IDs;
- parent node and incoming option, except at the root;
- the complete canonical action path from the root;
- a derived game-state snapshot;
- acting position;
- exact-combo ranges for relevant positions;
- supported action options;
- exact-combo strategy for the acting player;
- child-node mapping for actions that continue in the tree; and
- a terminal or boundary reason when the solution stops.

Boundary reasons distinguish a folded hand, an all-in terminal state, a completed preflop round, and a line not included by the artifact. An unsupported continuation is never presented as a solved state.

The node's state snapshot, actor, action options, ranges, and strategy must agree. A node can be loaded and cached without loading the complete solution, but it remains connected to the manifest and tree through verified references and hashes.

## Study contract

### `Scenario`

A scenario identifies a supported public decision point without specifying Hero's exact hole cards. It includes:

- schema and identity profile versions;
- deterministic scenario ID;
- game configuration, solution, and node IDs;
- Hero position, which must match the node actor;
- supported Study or Trainer modes; and
- optional non-identity discovery metadata such as title, description, and category tags.

The canonical scenario identity is based on its solution and node references. It does not copy ranges, strategy, or state. Those values resolve through the immutable node.

## Trainer contracts

### `DecisionResult`

A completed decision is immutable and uses a generated ID. It contains:

- schema version;
- result ID, session ID, and sequence number;
- scenario, game configuration, solution, and node IDs;
- exact Hero combo;
- offered action-option snapshot;
- selected option ID and resolved poker action;
- selected combo's reach weight;
- raw reference frequencies and action EVs for every offered option;
- highest-EV option;
- calculated EV loss;
- feedback severity;
- scoring-policy version;
- optional RNG roll and displayed mapping; and
- presented and answered UTC timestamps.

Illustrative compact result:

```json
{
  "schemaVersion": "1.0.0",
  "decisionResultId": "decision:018f4d8e-7c21-7a3b-a413-81b673d21f90",
  "trainingSessionId": "session:018f4d8d-9245-7fc0-a75a-fb0ac53de430",
  "sequence": 12,
  "scenarioId": "scenario:sha256:2a90b85e",
  "gameConfigId": "game:sha256:7f3a91c2",
  "solutionId": "solution:sha256:c14a680f",
  "nodeId": "node:sha256:0d6e34a9",
  "heroCombo": "As5s",
  "offeredOptions": [
    {
      "optionId": "fold",
      "inputKind": "FOLD",
      "resolvedAction": {
        "actor": "BB",
        "type": "FOLD",
        "isAllIn": false
      }
    },
    {
      "optionId": "call",
      "inputKind": "CALL",
      "resolvedAction": {
        "actor": "BB",
        "type": "CALL",
        "isAllIn": false
      }
    },
    {
      "optionId": "raise_11",
      "inputKind": "RAISE",
      "resolvedAction": {
        "actor": "BB",
        "type": "RAISE_TO",
        "targetBb": 11,
        "isAllIn": false,
        "raiseClassification": "FULL_RAISE"
      }
    }
  ],
  "selectedOptionId": "call",
  "selectedResolvedAction": {
    "actor": "BB",
    "type": "CALL",
    "isAllIn": false
  },
  "comboReachWeight": 1,
  "referenceSnapshot": [
    { "optionId": "fold", "frequency": 0.025, "actionEvBb": 0 },
    { "optionId": "call", "frequency": 0.55, "actionEvBb": 0.179 },
    { "optionId": "raise_11", "frequency": 0.425, "actionEvBb": 0.184 }
  ],
  "highestEvOptionId": "raise_11",
  "evLossBb": 0.005,
  "feedbackSeverity": "SMALL_EV_LOSS",
  "scoringPolicyVersion": "1",
  "presentedAt": "2026-08-17T18:00:00Z",
  "answeredAt": "2026-08-17T18:00:08Z"
}
```

The compact snapshot deliberately excludes the complete range and node. It retains everything needed to understand and recalculate the exact feedback:

```text
EV loss = max(snapshotted action EV) - selected action EV
```

If recalculation under the recorded scoring policy disagrees with stored EV loss or severity beyond approved tolerance, validation fails.

### `TrainingSession`

A session uses a generated ID and contains:

- schema version;
- status: `ACTIVE`, `COMPLETED`, or `ABANDONED`;
- scenario-selection rules;
- combo-sampling policy;
- feedback mode;
- scoring-policy version;
- ordered decision-result IDs;
- started and completed UTC timestamps; and
- a derived summary snapshot.

While active, decisions are append-only. Existing results cannot be edited or reordered. Once completed or abandoned, the session is immutable.

The summary may cache:

- decisions completed;
- total and average EV loss;
- severity counts;
- scenario and grouped-hand-class breakdowns; and
- frequency-calibration metrics when P0.8 sample requirements are met.

Every summary value must recalculate from ordered `DecisionResult` records. The summary is not authoritative.

## Canonical ingestion and validation

External data follows this boundary:

```text
Raw input
→ Parse
→ Explicit normalization
→ Structural validation
→ Poker-domain validation
→ Reference and strategy validation
→ Identity calculation
→ Canonical record
```

Normalization may perform documented conversions such as:

- `Cutoff` to `CO`;
- `K♠K♦` to `KsKd`;
- `2.50 BB` to `2.5 BB`; and
- currency amounts to BB when the source provides the blind level.

The normalization result reports every conversion. It cannot invent missing poker information or choose between conflicting values. Raw source data may be retained separately for diagnostics, but invalid or ambiguous data cannot drive Study, Trainer, or scoring.

### Validation levels

1. **Structural:** required fields, exact-decimal syntax, enum values, and supported schema versions.
2. **Poker domain:** cards, combos, positions, stacks, state replay, action order, legality, raise rules, and pot reconciliation.
3. **References:** configuration, solution, node, scenario, session, and result references exist and agree.
4. **Strategy:** combos are unique and possible; weights and probabilities are in range; frequencies cover all options and normalize; grading EVs exist.
5. **Replay:** action replay reproduces cached state; all-in and raise annotations match engine calculations.
6. **Trainer:** selected option was offered; snapshots match the referenced solution at creation; scoring and summaries recalculate.
7. **Integrity:** content identities and artifact hashes match canonical semantic content.

Canonical validation fails closed. Warnings are allowed only for non-authoritative metadata and cannot affect poker behavior, strategy, identity, or scoring.

### Structured errors

Failures return stable codes, precise paths, player/developer-readable messages, and safe diagnostic details:

```json
{
  "code": "POKER_RULE_ACTION_OUT_OF_TURN",
  "path": "actionHistory[3].actor",
  "message": "Expected BTN to act, but received SB.",
  "details": {
    "expected": "BTN",
    "received": "SB"
  }
}
```

Error-code families are:

- `PARSE_*`
- `NORMALIZATION_*`
- `SCHEMA_*`
- `POKER_RULE_*`
- `REFERENCE_*`
- `STRATEGY_*`
- `REPLAY_*`
- `INTEGRITY_*`
- `TRAINER_*`

No validation error silently repairs canonical input.

## End-to-end Trainer data flow

```text
Select Scenario
→ Resolve validated SolutionNode
→ Replay and validate GameState
→ Sample an exact combo from canonical range weights
→ Present the node's supported ActionOptions
→ User selects an input option
→ Resolve and validate the underlying poker action
→ Snapshot the selected combo's frequencies and EVs
→ Calculate EV loss and feedback under a versioned policy
→ Write immutable DecisionResult
→ Append its ID to the active TrainingSession
→ Recalculate the derived session summary
```

At no point may display-rounded values become the input to scoring or state calculation.

## Verification requirements

The later implementation and P0.8 corpus must verify that:

- equivalent normalized inputs produce identical content IDs;
- behaviorally different inputs produce different IDs;
- replay is deterministic;
- cached-state mismatches are rejected;
- all 1,326 exact combos map to the correct 169 grouped classes;
- exact suits survive dealing, feedback, history, and replay;
- duplicate and impossible combos are rejected;
- range aggregation uses exact combo counts and weights correctly;
- legal actions remain distinct from solution-supported options;
- fixed raise and all-in options resolve to exact canonical actions;
- all-in resolves correctly to a call, bet, full raise, or short raise;
- no two options in one node resolve to the same action;
- frequencies and EVs survive serialization without display rounding;
- solution-node references and integrity hashes agree;
- decision feedback recalculates from the compact snapshot;
- session summaries recalculate from immutable results; and
- serialize/parse round trips cause no semantic drift.

## Evolution path

The layered MVP can evolve without rewriting its semantic foundation:

- Postflop adds board cards, `BET_TO`, street transitions, and derived sizing presentation.
- Tournaments add chip-denominated configurations, antes, payouts, and ICM-specific value units in versioned contracts.
- Hand-history imports add source adapters before the canonical boundary.
- Production solving adds job and artifact-generation contracts around the same manifests and nodes.
- Event sourcing can later treat immutable resolved actions and decision results as events while retaining derived states and summaries as projections.

None of these future concerns changes the MVP rule that canonical content is exact, validated, versioned, and reproducible.

## Approval record

The project owner approved the design sections and the following revisions during collaborative review:

- Preserve all-in as a user-facing input while resolving its underlying action and retaining `isAllIn`.
- Remove stored small/large/pot-percentage sizing descriptions from canonical action options.
- Store the exact resolved action amount and derive presentation labels from node state.

On 2026-08-17, the project owner approved this written specification without further revisions.
