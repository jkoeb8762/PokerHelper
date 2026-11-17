# Primary User Persona and MVP Study Journey

**Status:** Approved  
**Approved:** 2026-08-16  
**Roadmap checkpoint:** P0.3

## Purpose

This document defines who PokerHelper's first release is designed for and the exact experience that release must support. It is a product decision, not a description of every person who may eventually use PokerHelper.

When a feature or design choice creates a tradeoff, the first release should favor this user and this study journey unless the roadmap is formally changed.

## Primary user persona

### Persona statement

> An improving recreational or intermediate No-Limit Texas Hold'em player who understands poker fundamentals but is not a solver expert. They play or study six-max cash games, want to improve their 100 BB preflop decisions, and use PokerHelper away from the table.

### User profile

| Attribute | Definition |
|---|---|
| Experience | Improving recreational or intermediate player |
| Primary game | Six-max No-Limit Texas Hold'em cash |
| Initial stack depth | 100 BB |
| Existing knowledge | Positions, blinds, starting hands, fold, call, raise, three-bet, and basic preflop action |
| Specialist knowledge | Solver algorithms and advanced EV mathematics are not assumed |
| Study environment | Desktop or laptop, away from an active poker table |
| Main motivation | Make stronger preflop decisions and understand why they are stronger |
| Preferred learning style | Focused decisions, immediate evidence-based feedback, repetition, and progress review |

### Core problem

The user can find static preflop charts, but charts alone do not provide a complete learning loop. They do not easily show how strategies change by action sequence, how mixed strategies should be practiced, how costly a mistake is, or which decisions the user repeatedly gets wrong.

PokerHelper should turn verified preflop strategy data into guided, repeatable practice with understandable feedback.

### User goals

The primary user wants to:

1. Practice a specific six-max 100 BB preflop situation.
2. Learn which actions are strategically supported for each starting hand.
3. Understand when a strategy mixes between multiple actions.
4. Distinguish a harmless frequency deviation from a costly strategic error.
5. Measure mistakes using action EV and EV loss.
6. Identify recurring weaknesses by position and action sequence.
7. Redrill weak situations until performance improves.

### User needs

The first release must provide:

- Plain-language navigation that does not require solver expertise
- Accurate positions, action history, pot, stacks, and legal actions
- A clearly identified source strategy and its assumptions
- Action frequencies and action EVs for the current hand
- Feedback that separates supported mixed actions from significant mistakes
- Saved sessions and reproducible historical results
- A direct path from an identified weakness to another focused drill

## Users not targeted by the first release

The initial product is not primarily designed for:

- A person who has not yet learned the rules and basic terminology of poker
- A professional solver researcher who needs to configure arbitrary game trees
- A tournament-only, heads-up-only, or Pot-Limit Omaha player
- A user seeking live table overlays, automated decisions, or real-time advice
- A user who initially requires postflop, multiway, or arbitrary-stack coverage

These exclusions prevent the MVP from expanding before its central study loop is reliable. They do not permanently exclude those audiences from later roadmap phases.

## MVP study journey

### Journey summary

> Select a supported situation → receive a hand → choose a legal action → inspect strategy and EV feedback → repeat → review the session → drill weaknesses.

### 1. Enter the study dashboard

The user opens PokerHelper and sees a clear way to begin or resume preflop training. The interface identifies the supported format as six-max cash at 100 BB and does not imply support for unavailable formats.

**User outcome:** The user understands what can be studied and can begin without knowing solver terminology.

### 2. Choose a preflop situation

The user chooses a supported hero position and action sequence. The application supplies the fixed game assumptions, including blinds, stack depth, rake preset, and available bet sizes.

An example situation is:

- Six-max cash
- 100 BB starting stacks
- Cutoff raises to 2.5 BB
- Button and small blind fold
- Hero is in the big blind

**User outcome:** The user knows exactly which decision is being practiced and under which assumptions.

### 3. Start the drill and receive a hand

PokerHelper deals Hero a possible exact starting-hand combo, such as `As5s`. The rank and suit of both cards are always shown; grouped labels such as `A5s` are reserved for range-level study and aggregation. Hands are sampled from the current scenario according to the documented training rules and never conflict with known cards.

**User outcome:** The user is presented with a valid decision from the selected situation.

### 4. Make a decision

The interface presents only actions that are legal and supported by the solution tree. For the example, these may include:

- Fold
- Call
- Raise to a supported size

The user selects an action without seeing the answer first unless a future learning-assistance option is deliberately enabled.

**User outcome:** The user commits to the same type of decision they are trying to learn.

### 5. Receive feedback

After the decision, PokerHelper shows:

- The strategy's frequency for each supported action
- The EV of each supported action
- The EV lost by the selected action relative to the best available action
- Whether the selection was preferred, supported as part of a mix, a small deviation, or a significant mistake
- A concise explanation written for a player rather than a solver researcher
- The assumptions and solution version needed to reproduce the result

The primary grading measure is:

```text
EV loss = EV of best available action - EV of chosen action
```

Frequency calibration is reported separately. A low-frequency action that remains part of the equilibrium strategy is not automatically treated as a major EV mistake.

**User outcome:** The user understands both what the reference strategy does and the practical cost of their choice.

### 6. Continue practicing

PokerHelper deals additional valid hands from the same situation. Repetition teaches the shape of the complete range rather than encouraging memorization of a single hand.

The user may continue, pause, or finish the session. The MVP does not need artificial game animation or unrelated table simulation.

**User outcome:** The user builds pattern recognition across a strategically related set of decisions.

### 7. Review the session summary

At the end of the session, PokerHelper summarizes:

- Number of decisions completed
- Total and average EV loss
- Preferred, mixed, marginal, and costly decisions
- Frequency-calibration performance where relevant
- Results grouped by supported hand class or scenario
- The decisions that deserve the most review

**User outcome:** The user can identify specific strengths and weaknesses rather than relying on a generic score.

### 8. Review and redrill mistakes

The user opens a prior decision to see its original situation, selected action, reference strategy, EV feedback, assumptions, and solution version. From that review, the user can start another drill focused on the same or a closely related supported situation.

**User outcome:** A detected weakness becomes an immediate, focused study action.

## MVP journey success criteria

The journey is successful when the primary user can, without outside instruction:

1. Identify the format and assumptions being studied.
2. Select a supported preflop scenario.
3. Understand the presented cards, positions, action history, and choices.
4. Submit a legal action.
5. Interpret the reference frequencies, action EVs, and personal EV loss.
6. Understand whether the action was supported, marginal, or meaningfully costly.
7. Complete and review a training session.
8. Start a targeted drill from a recorded weakness.

The longer-term learning outcome is a reduction in EV loss on held-out but related situations, not merely improved recall of hands the user has already seen.

## Design implications

This persona and journey create the following commitments for the MVP:

- The user interface will use familiar poker language and explain specialized metrics in context.
- The trainer is the central experience; the solution browser supports it rather than replacing it.
- Feedback will emphasize decision quality and EV cost, not a simplistic correct/incorrect score.
- The scenario context and solution assumptions will remain visible or readily inspectable.
- Historical results will retain their solution version so they remain reproducible.
- Study workflows will be optimized for desktop and laptop before native mobile applications.
- No feature will inspect or react to a live poker client or active hand.

## Related roadmap checkpoints

This decision informs, but does not complete:

- **P0.4:** Approve terminology and units used in the journey and feedback.
- **P0.5:** Define the data contracts that represent each journey state.
- **P0.7:** Create low-fidelity screens for each journey step.
- **P0.8:** Define tests and accuracy expectations for the displayed decisions and feedback.

## Approval record

On 2026-08-16, the project owner approved the primary user persona and proposed MVP study journey described in this document.
