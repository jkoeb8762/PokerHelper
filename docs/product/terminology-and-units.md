# Poker Terminology and Units

**Status:** Approved  
**Approved:** 2026-08-16  
**Roadmap checkpoint:** P0.4  
**Scope:** Six-max, 100 BB, preflop NLHE cash MVP

## Purpose

This document defines the language and units PokerHelper will use during scenario selection, training, feedback, and session review. It is a controlled product vocabulary rather than a general poker glossary.

The vocabulary must work from three perspectives:

- **Professional poker player:** Use familiar poker language and preserve strategically important distinctions.
- **Product manager:** Give each visible term one understandable meaning throughout the user journey.
- **Coder:** Give every concept stable semantics that can later map to data contracts, validation rules, and tests.

The project owner approved these conventions after revising dealt-hand notation to require the exact suit of both cards throughout the Trainer experience.

## Language conventions

1. Use the familiar poker term in the interface when it is unambiguous.
2. Explain specialized metrics such as EV the first time they appear and in an accessible tooltip thereafter.
3. Prefer explicit phrases over overloaded shorthand. For example, use **raise to 8 BB**, not **raise 8 BB**.
4. Use **reference strategy** rather than claiming that an approximate solver output is perfectly GTO.
5. Use **most frequent action** and **highest-EV action** as separate terms; they are not guaranteed to be the same action.
6. Use **EV loss** for decision cost. Do not use **regret** as the primary player-facing label.
7. Do not label a strategically mixed decision simply **correct** or **incorrect**.
8. Use **Hero** for the user. Refer to other players by position when possible rather than using the generic label **Villain**.
9. Use title case for screen and control names, but normal sentence case for poker concepts and feedback.
10. Define postflop, tournament, ICM, and solver-research vocabulary when those roadmap phases begin; do not overload the MVP with unused terminology.

## Core study-journey terms

| Player-facing term | Meaning in PokerHelper | Product and implementation rule |
|---|---|---|
| **Format** | The game family and table structure being studied | MVP format is six-max NLHE cash. Format is part of every scenario's identity. |
| **Game assumptions** | Rules and parameters under which the reference strategy was generated | Includes format, seats, blinds, stacks, rake, action sizes, source, and solution version. Must remain inspectable. |
| **Scenario** | A public preflop setup to practice, independent of Hero's exact hole cards | Includes game assumptions, positions, action history, player to act, and supported actions. One scenario can generate many decisions. |
| **Spot** | Conversational synonym for a poker situation | Player-facing copy may use spot. Formal product requirements should use scenario or decision when the distinction matters. |
| **Decision** | One training opportunity within a scenario | Consists of the scenario, Hero's exact two-card combo, available actions, selected action, and solution version. |
| **Decision point** | The moment at which a player must act | Preferred player-facing term when explaining an action-tree location. |
| **Node** | Internal action-tree location corresponding to a decision point | Use in developer and advanced diagnostic views; avoid requiring the primary user to understand it. |
| **Drill** | A configured series of related training decisions | Stores scenario-selection and sampling rules, not the user's results. |
| **Training session** | A bounded sequence of completed decisions | Begins when training starts and ends when the user finishes or abandons it. Pausing does not create a new session by itself. |
| **Session summary** | Aggregated results for one training session | Must be reproducible from stored decision results and their solution versions. |
| **Review** | Inspection of a previously completed decision or session | Must show the original state, choice, feedback, and solution version. |
| **Reference strategy** | The validated solver-derived strategy used for study and grading | Never imply mathematical exactness beyond the solution's documented accuracy. |
| **Solution** | A versioned strategy artifact for a defined game tree and assumptions | The solution, configuration, accuracy metadata, and source are inseparable. |
| **Solution version** | Immutable identifier for the exact reference data used | Historical feedback always retains this identifier. |
| **Supported** | Directly represented and validated by the selected solution | Never use supported to describe a nearest or silently substituted scenario. |
| **Out of tree** | An action or state not represented by the solution's configured action tree | The application must say this explicitly instead of presenting an exact answer. |

## Game and table terminology

### Game name

- Full name: **No-Limit Texas Hold'em**
- Accepted short name in compact UI: **NLHE**
- Table size: **six-max**
- Game type: **cash**
- Standard MVP label: **Six-Max 100 BB NLHE Cash**

Use **six-max** for the table format even when fewer than six players remain in an individual action sequence.

### Positions

PokerHelper uses the following position names and abbreviations for six-max:

| Preflop order | Full name | UI abbreviation | Meaning |
|---:|---|---|---|
| 1 | Under the Gun | **UTG** | First player to act preflop at a six-handed table |
| 2 | Hijack | **HJ** | Seat after UTG |
| 3 | Cutoff | **CO** | Seat immediately before the button |
| 4 | Button | **BTN** | Dealer-button position |
| 5 | Small Blind | **SB** | Posts the small blind |
| 6 | Big Blind | **BB** | Posts the big blind and acts last in an unopened preflop round |

Rules:

- Use abbreviations in matrices, action histories, and compact controls.
- Show the full name in tooltips and introductory copy.
- **BB** can mean either the big-blind position or the big-blind unit. Context must make the meaning unambiguous. In code and accessibility labels, use distinct names such as `BIG_BLIND_POSITION` and `bigBlindAmount`.
- The user is **Hero**. Other players should normally be identified as UTG, HJ, CO, BTN, SB, or BB.

### Forced bets and stacks

| Term | Definition |
|---|---|
| **Small blind** | The smaller mandatory preflop contribution; `0.5 BB` in the MVP unless the selected solution states otherwise |
| **Big blind** | The larger mandatory preflop contribution and the base unit for normalized chip amounts; `1 BB` |
| **Starting stack** | A player's stack immediately before posting blinds or other forced bets |
| **Stack behind** | Chips currently available to a player after all contributions already committed at the decision point |
| **Starting effective stack** | The smaller starting stack among the players relevant to the contested betting line, measured before forced bets |
| **Current effective stack** | The smaller current stack behind among players who can still contest additional betting at the decision point |

Rules:

- The MVP's **100 BB** label means a 100 BB starting stack before blinds are posted.
- Avoid the unqualified label **effective stack** when it could mean either starting or current effective stack.
- Never call the pot or committed chips part of the stack behind.

### Pot terminology

| Term | Definition |
|---|---|
| **Current pot** | All chips committed to the hand before Hero takes the pending action, including a wager Hero is facing |
| **Amount to call** | Additional chips Hero must commit to match the current wager |
| **Pot after calling** | Current pot plus Hero's amount to call |
| **Dead money** | Chips in the pot contributed by a player who can no longer win them, normally because that player folded |

For the MVP, displayed pot and call amounts are derived by the poker engine, not copied from descriptive text.

## Card and range terminology

### Ranks and suits

- Ranks use: `2 3 4 5 6 7 8 9 T J Q K A`
- `T` means ten.
- Compact suit codes use: `s h d c`, meaning spades, hearts, diamonds, and clubs.
- An exact two-card combo is displayed in compact rank-and-suit notation, such as `KsKd` or `AsKs`.
- Visual card components may additionally render `♠ ♥ ♦ ♣`, but their visible text or accessible label must retain the exact rank and suit of each card.

Color must not be the only way suits are distinguished; rank-and-suit text and accessible labels are required.

### Starting-hand notation

| Example | Meaning |
|---|---|
| `KK` | The grouped class containing any pair of kings |
| `AKs` | The grouped class containing any suited ace-king combo |
| `AKo` | The grouped class containing any offsuit ace-king combo |
| `KsKd` | The exact king-of-spades/king-of-diamonds combo |
| `AsKs` | The exact ace-of-spades/king-of-spades combo |

Rules:

- Grouped starting-hand classes are used in range matrices, filters, calculations, and aggregate study views.
- Pocket-pair classes have no `s` or `o` suffix.
- Non-paired grouped classes always include `s` or `o` when suit relationship matters.
- Every dealt hand in Trainer is an exact combo: each card must include its rank and suit. Trainer must show `KsKd`, never only `KK`, and `AsKs`, never only `AKs`.
- The exact combo must remain visible in immediate feedback, decision history, session review, and replay.
- Exact-combo notation uses two consecutive rank-and-suit card codes with no separator or `s`/`o` class suffix.
- For non-paired combos, display the higher-ranked card first. For pairs, use the stable suit order `s`, `h`, `d`, `c`.
- Range-level reports may aggregate exact combos into their grouped starting-hand class, but the underlying decision must retain the exact combo.

### Range concepts

| Term | Definition |
|---|---|
| **Combo** | One exact two-card holding, including both suits; there are 1,326 possible NLHE starting combos before card removal |
| **Starting-hand class** | A rank-and-suitedness grouping such as `A5s`, `KQo`, or `77`; there are 169 classes |
| **Range** | A weighted set of possible combos for a player at a decision point |
| **Range weight** | The remaining relative presence of a combo in a range, represented as a probability-like value |
| **Card removal** | Removal of combos made impossible by known cards |

Do not use **hand** alone in technical requirements when it could mean an exact combo, a starting-hand class, or a complete hand record.

## Preflop action terminology

### Player actions

| Action | Definition and UI convention |
|---|---|
| **Fold** | Surrender the hand and any chips already committed |
| **Check** | Continue without adding chips when no call is required; normally only available to the BB in an unraised preflop pot |
| **Call** | Add exactly the amount required to match the current wager |
| **Raise to _X_ BB** | Increase the player's total contribution on the current street to _X_ BB |
| **All-in** | Commit the entire stack behind; it may be a call or raise and should retain that underlying action type in the data model |

Critical sizing rule:

> A displayed raise size is always the player's total contribution **to** that amount on the current street, never the additional amount being added.

For example, after an open to `2.5 BB`, **Raise to 10 BB** means the raiser's total preflop contribution becomes `10 BB`.

### Action-sequence terms

| Term | Definition |
|---|---|
| **Unopened pot** | No player has voluntarily entered the pot yet |
| **Limp** | Enter an unopened pot by calling the big blind |
| **Raise first in (RFI)** | Make the first voluntary raise when all prior players have folded |
| **Open raise** | Familiar synonym for RFI; preferred in natural feedback, with RFI available in compact labels |
| **Three-bet (3-bet)** | The first re-raise after an initial raise; the blinds conceptually count as the first bet |
| **Four-bet (4-bet)** | A re-raise of a 3-bet |
| **Cold call** | Call a raise without having previously invested voluntarily in that betting round |
| **Squeeze** | Re-raise after a raise and at least one call |

Rules:

- In preflop UI, use **raise**, not **bet**, for the first voluntary aggressive action.
- Use **open raise** in sentences and **RFI** where compact terminology helps experienced players.
- Action history should be explicit, for example: `UTG folds → HJ folds → CO raises to 2.5 BB → BTN folds → SB folds → Hero (BB) to act`.
- The solution determines which limps, calls, and raise sizes are supported. Familiar terminology does not imply that every action is in the MVP tree.

### Legal and supported actions

| Term | Definition |
|---|---|
| **Legal action** | Permitted by poker rules in the current state |
| **Supported action** | Present in the selected solution's action tree |
| **Available action** | Both legal and supported; therefore shown as a training choice |

An action can be legal poker but unavailable in a drill because the reference solution did not include that size. The interface should say **Size not included in this solution**, not **Illegal raise**, in that case.

## Units and numeric conventions

### Primary units

| Quantity | Player-facing unit | Semantic/internal unit | Example |
|---|---|---|---|
| Stack, pot, wager, and call amount | Big blinds | Exact chip amount normalized by configured big blind | `100 BB`, `4 BB`, `2.5 BB` |
| Action frequency | Percent | Probability in `[0, 1]` | `37.4%` |
| Range weight | Percent when shown | Weight in `[0, 1]` | `50%` |
| Action EV | Big blinds | Signed expected value from the current decision point | `+0.143 BB` |
| EV loss | Big blinds | Non-negative difference between best and selected action EV | `0.012 BB` |
| Frequency deviation | Percentage points | Signed difference between observed and reference frequencies | `+8.0 pp` |
| Rake rate | Percent | Rate in `[0, 1]` | `5%` |
| Rake cap | Big blinds | Exact configured chip amount normalized to BB | `1 BB` |
| Decision count | Integer decisions | Non-negative integer | `40 decisions` |

### Big blinds and chips

- The primary display unit is **BB**, not dollars or site-specific chips.
- `1 BB` equals the configured big blind for that solution.
- The MVP normally displays the small blind as `0.5 BB` and the big blind as `1 BB`.
- Player-facing amounts omit unnecessary trailing zeros: `3 BB`, not `3.0 BB`; `2.5 BB` remains decimal.
- Calculations must use exact configured chip amounts or fixed-precision values. Binary floating-point display values must not become the source of truth for pot or stack accounting.
- The exact storage representation will be approved in P0.5; this document fixes the semantic unit, not the programming type.

### Percent and percentage points

- Use **percent (`%`)** for a portion of a whole, such as an action occurring `40%` of the time.
- Use **percentage points (`pp`)** for the absolute difference between two percentages.
- A change from `40%` to `50%` is `+10 pp`, not `+10%`.
- Do not use percentage points for EV loss.

### Display precision

| Value | Default display |
|---|---|
| Whole or half-BB stack/wager | Minimum needed precision, such as `100 BB` or `2.5 BB` |
| Pot with finer configured chips | Up to the exact precision supported by the game configuration |
| Action frequency | One decimal place, such as `37.4%` |
| Individual action EV | Signed, three decimal places, such as `+0.143 BB` or `-0.025 BB` |
| Per-decision EV loss | Three decimal places, such as `0.012 BB` |
| Session total EV loss | Two decimal places by default, with more precision available in detail |
| Average EV loss | Three decimal places and labeled `BB/decision` |
| Frequency deviation | One decimal place and labeled `pp` |

Rounding rules:

1. Calculate and compare using unrounded source values.
2. Round only for display.
3. Sum unrounded decision values before rounding session totals.
4. Display an EV loss smaller than the visible precision as `<0.001 BB`, not `0.000 BB`.
5. EV loss cannot be negative. A negative result beyond numeric tolerance is a data or calculation error.
6. When independently rounded strategy frequencies would not total `100.0%`, use a deterministic display-rounding method while preserving the unrounded values in details.
7. Do not determine whether actions are equivalent by comparing their rounded display values.

## Strategy terminology

| Term | Definition |
|---|---|
| **GTO** | Game-theory optimal; an equilibrium strategy that cannot be profitably exploited by unilateral deviation under the modeled game assumptions |
| **Approximate equilibrium** | A solver-derived strategy that approaches equilibrium within a documented accuracy measure |
| **Action frequency** | How often the reference strategy takes an action with the selected combo at the current decision point |
| **Range action frequency** | How often an action is taken across the player's entire weighted range at that decision point |
| **Pure strategy** | One material action after accounting for the solution's numerical support/noise threshold |
| **Mixed strategy** | Two or more material actions for the same combo at the same decision point |
| **Most frequent action** | Action with the highest reference frequency |
| **Highest-EV action** | Action with the highest unrounded action EV |
| **Strategy support** | Actions assigned meaningful positive frequency beyond the solution's documented numerical noise threshold |

Rules:

- **GTO** may describe the learning objective. **Reference strategy** is the normal label for the concrete strategy displayed by the product.
- A solution's support/noise threshold and accuracy standard will be fixed under P0.8; the UI must not treat solver numerical residue as a meaningful mix.
- The most frequent action may differ from the numerically highest-EV action because supported equilibrium actions can be nearly indifferent and because solutions have finite convergence accuracy.
- Never infer action quality from frequency alone. A low-frequency supported action can have negligible EV loss.
- Always distinguish **combo action frequency** from **range action frequency** in labels and code.

## EV and feedback terminology

### Expected value baseline

**Action EV** is the expected change in Hero's stack from the current decision point forward, measured in BB, with chips committed before the decision treated as sunk.

Under this decision-point convention:

- Folding has an action EV of `0 BB` from the current decision forward.
- Prior blind or wager contributions are not charged again in the displayed action EV.
- Positive action EV means an expected gain from continuing relative to surrendering at that decision point.
- The EV difference between actions is independent of a constant baseline shift, which makes EV loss reproducible even if a source artifact originally used another baseline.

Use the explicit internal name **decision-point action EV**. Do not mix it with **hand EV from before forced bets**, which is a different measure and is outside the MVP feedback requirement.

### Decision feedback terms

| Term | Definition |
|---|---|
| **Selected action** | Action submitted by the user |
| **Action EV** | Decision-point expected value of a particular available action |
| **EV loss** | Highest available action EV minus selected action EV |
| **EV-equivalent** | Actions whose EV difference falls within the approved numeric/solver tolerance |
| **Frequency deviation** | Difference between a user's observed action frequency and the reference frequency over comparable repeated decisions |
| **Most costly decision** | A completed decision ranked highly by EV loss, not merely by rarity of the selected action |

Canonical formula:

```text
EV loss = max(action EV across available actions) - selected action EV
```

Feedback principles:

1. EV loss is the primary decision-cost measure.
2. Strategy frequency supplies context but is not itself the cost of the action.
3. A single mixed decision cannot prove that the user followed or failed a target frequency. Frequency performance requires repeated comparable opportunities.
4. The app should explain when the user's action is part of the reference mix even if it is not the most frequent action.
5. Session total EV loss is a training aggregate, not a claim about money actually lost in a poker session.

### Proposed feedback severity labels

The following labels are proposed; numeric boundaries will be established and validated under P0.8:

1. **No material EV loss** — selected action is EV-equivalent within the approved tolerance.
2. **Small EV loss** — measurable but strategically minor cost.
3. **Significant mistake** — meaningful expected-value cost deserving review.
4. **Major mistake** — high expected-value cost and a priority for redrilling.

Avoid these labels in the MVP:

- **Correct percentage:** Misleading for mixed strategies.
- **GTO score:** Undefined unless a transparent and validated formula is approved later.
- **Bad play:** Judgmental and less informative than the EV cost.
- **Wrong action:** Reserve **invalid** for actions that are not available; use EV-based language for strategy feedback.

## Session and progress metrics

| Metric | Definition | Unit |
|---|---|---|
| **Decisions completed** | Number of decisions for which the user submitted an available action | decisions |
| **Total EV loss** | Sum of unrounded per-decision EV losses in the session | BB |
| **Average EV loss** | Total EV loss divided by decisions completed | BB/decision |
| **EV loss per 100 decisions** | Average EV loss multiplied by 100 | BB/100 decisions |
| **Observed action frequency** | Times the user selected an action divided by comparable opportunities | % |
| **Frequency deviation** | Observed action frequency minus reference action frequency | pp |
| **Absolute frequency deviation** | Absolute value of frequency deviation | pp |

Rules:

- Label `BB/100 decisions` in full at first use. It is a trainer metric, not the poker win-rate statistic `BB/100 hands`.
- Do not calculate frequency calibration across unrelated scenarios, combos, or strategy versions.
- Do not show frequency calibration when the sample is too small to be meaningful; the minimum sample and aggregation method belong to P0.8.
- Always show sample size beside aggregate performance.
- Prefer a breakdown of costly scenarios over one opaque overall score.

## Random-number aid

**RNG** means random number generator. In PokerHelper it is an optional study aid for executing a mixed strategy, not a score and never a live-play automation feature.

Proposed convention:

- Display an independent roll from `1` through `100`.
- Map contiguous number bands to actions using the displayed strategy frequencies and a deterministic rounding rule.
- Show the mapping, for example: `1–37 Raise · 38–92 Call · 93–100 Fold`.
- Keep the exact unrounded reference frequencies available even when integer RNG bands require rounding.
- Never choose or submit the user's action automatically.

The RNG display and mapping should be confirmed during P0.7 wireframing and tested under P0.8.

## Rake terminology

| Term | Definition |
|---|---|
| **Rake** | Amount removed from qualifying cash-game pots by the game operator |
| **Rake rate** | Percentage applied under the configured rake rules |
| **Rake cap** | Maximum rake collected from a qualifying pot under the configured rules |
| **Rake preset** | Versioned bundle of rate, cap, collection timing, player-count rules, and any no-flop-no-drop behavior |

Rules:

- Do not describe a solution only as `5% rake`; rate without cap and collection rules is incomplete.
- The Study and Trainer views must identify the selected rake preset.
- EV displayed from a raked solution is **rake-adjusted** under that preset; it is not a universal value for all cash games.
- The exact MVP rake preset is a separate configuration decision and must be documented before solution generation.

## Example scenario and feedback copy

The values below are illustrative formatting examples only; they are not approved strategy data.

```text
BB vs CO Open
Six-Max NLHE Cash · 100 BB · MVP Rake Preset

Action history
UTG folds → HJ folds → CO raises to 2.5 BB → BTN folds → SB folds

Hero: BB · As5s
Current pot: 4 BB · Call amount: 1.5 BB

Available actions       Frequency       Action EV
Fold                         2.5%         0.000 BB
Call                        55.0%        +0.179 BB
Raise to 11 BB              42.5%        +0.184 BB

You chose: Call
EV loss: 0.005 BB

Small EV loss. Calling is part of the reference mix and is nearly
EV-equivalent to raising in this solution.
```

This example demonstrates the intended separation between:

- exact scenario context;
- amount to call versus raise-to size;
- reference frequency versus action EV;
- selected action versus highest-EV action; and
- measurable EV difference versus harsh correct/incorrect grading.

## Terms deliberately deferred

The following will receive dedicated definitions when their phases are scoped:

- Equity, range equity, equity realization, and pot odds
- Board texture, blockers, draws, and made-hand categories
- Bet size as a percentage of pot
- Stack-to-pot ratio
- Multiway pots and side pots in player-facing analysis
- Tournament chip EV, monetary EV, ICM equity, risk premium, and bounty EV
- Nodelocking, exploitability, convergence, and solver accuracy metrics

The engine may need some of these concepts earlier, but they should not appear in MVP feedback without an approved user-facing definition.

## Approved conventions

The project owner approved the following decisions:

- [x] Use **BB** as the primary amount and EV unit.
- [x] Treat **100 BB** as the starting stack before forced bets.
- [x] Display every raise as **raise to _X_ BB**.
- [x] Use decision-point action EV, with prior contributions treated as sunk and fold EV equal to `0 BB`.
- [x] Use EV loss as the primary grading measure and assess frequency calibration separately.
- [x] Adopt the proposed four feedback-severity labels, with numeric thresholds deferred to P0.8.
- [x] Use one decimal place for frequencies and three decimal places for per-decision EV/EV loss.
- [x] Use percentage points for differences between frequencies.
- [x] Use an optional `1–100` RNG roll without automating the user's choice.
- [x] Prefer **reference strategy** over an unsupported claim of exact GTO play.
- [x] Use the six-max positions and grouped starting-hand classes defined above.
- [x] Require exact rank-and-suit combos such as `KsKd` and `AsKs` whenever Trainer deals or reviews a hand.
- [x] Keep the listed postflop, tournament, and research terminology deferred.

## Approval record

On 2026-08-16, the project owner approved all proposed terminology and unit conventions with one revision: grouped classes such as `KK` and `AKs` remain valid for range-level study, but Trainer deals, feedback, history, and replay must always identify the exact combo, such as `KsKd` or `AsKs`.
