# MVP Low-Fidelity Wireframes

**Status:** Approved for implementation  
**Date:** 2026-11-17  
**Roadmap checkpoint:** P0.7

## Purpose

These wireframes turn the approved MVP journey into five desktop-responsive
screens. They define information hierarchy, controls, states, and navigation;
they do not define final visual styling.

```text
Scenario Selection → Study View ─┐
        │                        │
        └──────────────→ Trainer → Feedback → next hand
                                      │
                                      └→ Session Review → redrill
```

## Shared application shell

```text
┌──────────────────────────────────────────────────────────────────────┐
│ PokerHelper   Study   Train   Sessions                 Local · v0.x │
├──────────────────────────────────────────────────────────────────────┤
│ [Page title]                                  [Assumptions / Help]   │
│                                                                      │
│                         page content                                 │
└──────────────────────────────────────────────────────────────────────┘
```

The active destination is visible in text and not color alone. The main region
receives keyboard focus after navigation. `Assumptions` opens a non-destructive
panel with format, blinds, stacks, rake, tree, source, and solution version.

## Screen 1 — Scenario selection

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Choose a preflop situation                                           │
│ Six-Max NLHE Cash · 100 BB · MVP Rake Preset                        │
├───────────────────────────┬──────────────────────────────────────────┤
│ HERO POSITION             │ ACTION SEQUENCE                          │
│ ( ) UTG  ( ) HJ  ( ) CO   │ 1. UTG folds                            │
│ ( ) BTN  ( ) SB  (●) BB   │ 2. HJ folds                             │
│                           │ 3. CO raises to [2.5 BB ▾]              │
│ SPOT                      │ 4. BTN folds                             │
│ [BB vs CO open         ▾] │ 5. SB folds                             │
│                           │                                          │
│ Available: opening,       │ Hero to act: BB                          │
│ calling, raising spots    │ Pot 4 BB · Call 1.5 BB                  │
├───────────────────────────┴──────────────────────────────────────────┤
│ [Study range]                                      [Start 20 hands] │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- Only supported scenarios appear; unavailable formats are not disabled bait.
- Selecting a named spot updates the readable action sequence and derived pot.
- `Study range` opens the same solution node without a dealt hand.
- The primary action states the drill length and remains changeable before
  starting.
- Validation errors appear next to the affected control and preserve choices.

## Screen 2 — Study view

```text
┌──────────────────────────────────────────────────────────────────────┐
│ BB vs CO Open                    CO raises to 2.5 BB → folds to BB   │
│ Pot 4 BB · Call 1.5 BB · BB has 99 BB behind         [Assumptions] │
├───────────────────────────────────────────┬──────────────────────────┤
│ RANGE MATRIX                              │ SELECTED HAND: A5s       │
│      A  K  Q  J  T  9  8  7  6  5 ... 2 │ Exact combos: 4          │
│ A   [AA][AKs] ...                         │                          │
│ K   [AKo][KK ] ...  selected → [A5s]      │ Fold       2.5%  0.000  │
│ ...                                       │ Call      55.0% +0.179  │
│ Each cell shows a segmented strategy      │ Raise 11  42.5% +0.184  │
│ and an accessible text equivalent.        │                          │
│                                           │ [Exact combo: As5s ▾]   │
├───────────────────────────────────────────┴──────────────────────────┤
│ Legend: Fold · Call · Raise to 11 BB                 [Train this]   │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- The 13×13 matrix is a grouped 169-class presentation backed by exact combos.
- Selecting a class shows its weighted aggregate; selecting an exact combo
  shows suit-specific values without losing the class context.
- Frequency and EV columns have explicit labels and units.
- The action history and assumptions remain visible or one action away.
- The matrix is keyboard navigable as a grid and has a non-color text summary.

## Screen 3 — Trainer decision

```text
┌──────────────────────────────────────────────────────────────────────┐
│ BB vs CO Open                                Hand 7 of 20 · 01:42   │
│ CO raises to 2.5 BB → BTN folds → SB folds → Hero BB               │
│ Pot 4 BB · Call 1.5 BB · Hero has 99 BB behind                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                         ┌────┐ ┌────┐                                │
│                         │ A♠ │ │ 5♠ │                                │
│                         └────┘ └────┘                                │
│                                                                      │
│                 [Fold]       [Call 1.5 BB]       [Raise to 11 BB]   │
│                                                                      │
│                 [Show RNG]                          [End session]    │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- Exact rank and suit are always visible and announced as `As5s`.
- Only legal solution-supported actions are buttons. The poker engine still
  independently validates the submitted option.
- The answer is hidden before submission.
- Keyboard shortcuts are optional and must be shown beside controls when on.
- `Show RNG` reveals a study aid but never selects or submits an action.
- Ending early requires confirmation only when an unsaved decision exists.

## Screen 4 — Decision feedback

```text
┌──────────────────────────────────────────────────────────────────────┐
│ As5s · You chose Call                       Small EV loss · 0.005 BB │
│ Calling is part of the reference mix and is nearly EV-equivalent.   │
├──────────────────────────────────────────────────────────────────────┤
│ ACTION            REFERENCE       ACTION EV          RESULT          │
│ Fold                  2.5%          0.000 BB                          │
│ Call                 55.0%         +0.179 BB         Your choice     │
│ Raise to 11 BB       42.5%         +0.184 BB         Highest EV      │
├──────────────────────────────────────────────────────────────────────┤
│ EV loss = 0.184 − 0.179 = 0.005 BB                                  │
│ Solution preflop-6m-100-v1 · decision-point EV       [Assumptions] │
│                                                                      │
│ [Review range]                                      [Next hand]     │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- Feedback separates reference frequency from action EV and EV loss.
- Supported low-frequency actions are never labelled simply wrong.
- The full-precision snapshot drives scoring; displayed rounding is explanatory.
- Severity includes an icon/text label and concise player-language explanation.
- `Next hand` is the primary action and is available without a mouse.

## Screen 5 — Session review

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Session complete · BB vs CO Open                   20 decisions      │
├──────────────────────────────────────────────────────────────────────┤
│ Total EV loss       Average loss       EV loss / 100 decisions      │
│ 0.640 BB            0.032 BB           3.200 BB                      │
├───────────────────────────────┬──────────────────────────────────────┤
│ PRIORITY REVIEW               │ DECISIONS                            │
│ AJo  0.220 BB  Major          │ Filter [All ▾] Sort [EV loss ▾]     │
│ K9s  0.090 BB  Significant    │ #  Hand Choice  Ref mix    EV loss  │
│ 76s  0.050 BB  Small          │ 4  AJo  Fold    Call/Raise  0.220   │
│                               │ 9  K9s  Call    Fold/Raise  0.090   │
│ [Redrill priority hands]      │ ...                                  │
├───────────────────────────────┴──────────────────────────────────────┤
│ [Back to scenarios]                    [Repeat spot] [Start redrill] │
└──────────────────────────────────────────────────────────────────────┘
```

Rules:

- Every aggregate shows its sample size and unit.
- Frequency calibration is hidden below its P0.8 minimum sample.
- A decision row opens the exact historical cards, state, snapshot, solution
  version, and calculation used at completion.
- Redrill creates a new session; it never mutates the original.

## Loading, empty, and error states

| State | Required behavior |
|---|---|
| First run with no solutions | Explain that a validated solution pack is required; offer an import action, not fabricated examples |
| Loading node | Preserve scenario context, show a labelled progress state, prevent duplicate submission |
| Invalid/corrupt artifact | Block Study and Trainer, show integrity code and remediation |
| Save failure | Keep the completed result in memory, offer retry/export diagnostics, do not silently continue |
| No sessions | Explain what a session records and link to scenario selection |
| Unsupported branch | Label it unsupported and return to the nearest supported decision; never approximate silently |

## Responsive behavior

Desktop is primary. Below roughly 800 px, two-column layouts stack with context
and actions before secondary detail. The range matrix may use contained
horizontal scrolling but the action legend and selected-hand detail remain
visible. At 320 px, exact cards, legal-action buttons, feedback, and the primary
next action must remain usable without page-level horizontal scrolling.

## Accessibility acceptance criteria

- All flows work by keyboard with a visible focus indicator.
- Page title and feedback result receive logical focus/announcement.
- Cards have readable text equivalents; suits do not rely on red/black alone.
- Strategy segments have labels or an accessible data table.
- Controls meet a minimum 44×44 CSS-pixel coarse-pointer target.
- Error and result announcements use appropriate live regions without repeating
  every visual update.
- Reduced-motion preference is honored.

## Contract traceability

| Screen | Primary canonical data |
|---|---|
| Scenario selection | `Scenario`, derived `GameState` |
| Study | `SolutionNode`, `Range`, `ActionOption`, `Strategy` |
| Trainer | `Scenario`, exact combo, legal actions, supported options |
| Feedback | immutable `DecisionResult` snapshot and scoring policy |
| Session review | `TrainingSession`, referenced immutable decisions |

## Approval record

The screen set follows the owner-approved persona, eight-step study journey,
terminology, and P0.5 contracts. On 2026-11-17 the owner delegated completion
through P1.10, so these low-fidelity interaction details are approved as the MVP
implementation baseline.
