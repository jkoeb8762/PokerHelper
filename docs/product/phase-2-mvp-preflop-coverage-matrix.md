# Phase 2 MVP Preflop Coverage Matrix

**Status:** Approved  
**Date:** 2026-11-19  
**Roadmap checkpoint:** P2.11

## Decision

The MVP directly teaches the three highest-priority six-max preflop decision
families:

1. raise first in (RFI), including the special unopened-small-blind case;
2. facing one open raise; and
3. the original raiser facing one 3-bet.

Cold-call-plus-raise, squeeze, overcall, cold-4-bet, direct versus-4-bet, and
multiway-postflop drills are deferred from the user-facing MVP. They are not
assumed to be mistakes or removed from the underlying payoff model when they
can change the value of an exposed decision.

This separates two scopes:

- **Study coverage** is the compact set of situations a user can select and
  train.
- **Computational support** includes later and off-path actions needed to
  calculate those situations honestly.

## Fixed game assumptions

| Assumption | MVP value |
|---|---|
| Format | Six-max no-limit hold'em cash |
| Seats | UTG, HJ, CO, BTN, SB, BB |
| Starting stacks | 100 BB for every seat |
| Blinds | 0.5 BB / 1 BB |
| Ante | None |
| Rake | `MVP_CASH_5PCT_1BB_NFND_V1` |
| Hand representation | 169 grouped classes for range study; exact rank-and-suit combos for Trainer and history |

This pack is specifically a raked cash-game model. It must not be presented as
an early-tournament, ante, ICM, or unraked-home-game strategy. Antes and the
absence of rake materially change calling incentives and therefore require
separate future solution packs.

## MVP action abstraction

The first pack uses one normal raise target per position relationship. This
keeps the solve and the study task understandable while preserving the most
important in-position/out-of-position distinction.

| Decision | Supported target |
|---|---:|
| Open raise | Raise to 2.5 BB |
| 3-bet when the 3-bettor will be in position postflop | Raise to 8 BB |
| 3-bet when the 3-bettor will be out of position postflop | Raise to 11 BB |
| 4-bet when the 4-bettor will be in position postflop | Raise to 22 BB |
| 4-bet when the 4-bettor will be out of position postflop | Raise to 24 BB |
| 5-bet | All-in |

Targets are total preflop contributions, not increments. BB is in position
against SB postflop and out of position against every other opener. All other
IP/OOP labels follow normal postflop action order.

The unopened SB decision may include fold, complete, and raise to 2.5 BB. Open
limping from UTG through BTN is excluded from this action abstraction. Facing
an open includes fold, call, and the supported 3-bet. Facing a 3-bet includes
fold, call, the supported 4-bet, and an all-in 4-bet when the source tree
supports it. The player facing a 4-bet must retain fold, call, and 5-bet-all-in
responses internally.

These sizes define the game being solved; they are not a claim that every size
is globally optimal. PokerHelper reports strategy and EV relative to this
declared action tree.

## User-facing scenario matrix

### A. Unopened pot / RFI — 5 scenarios

| Hero | Required prior action |
|---|---|
| UTG | None |
| HJ | UTG folds |
| CO | UTG and HJ fold |
| BTN | UTG, HJ, and CO fold |
| SB | UTG, HJ, CO, and BTN fold |

BB has no RFI decision when action folds to it; BB checks and sees a flop.

### B. Facing one open — 15 position pairs

| Opener | Supported Hero positions |
|---|---|
| UTG | HJ, CO, BTN, SB, BB |
| HJ | CO, BTN, SB, BB |
| CO | BTN, SB, BB |
| BTN | SB, BB |
| SB | BB |

All players who act between the opener and Hero have folded. When seats remain
to act behind Hero, their possible folds, calls, overcalls, squeezes, and later
responses remain part of the solver tree even though they are not separate MVP
drills.

### C. Original raiser facing one 3-bet — 15 position pairs

The supported opener/3-bettor pairs are the same 15 ordered pairs listed
above. Hero is the original raiser, one later seat 3-bets, and every other seat
folds before action returns to Hero.

This category does not include a player cold-calling or cold-4-betting after
someone else opened and another player 3-bet.

### Coverage total

The MVP exposes **35 scenario families**: 5 unopened-pot decisions, 15
versus-open decisions, and 15 original-raiser-versus-3-bet decisions. A
scenario family contains the complete 169-class range and every exact combo,
not one scenario per hand.

## Required computational support

Even though the UI exposes only the 35 families above, an acceptable source
must account for all reachable branches that can materially change their EVs:

- responses by every seat still to act after an RFI or versus-open decision;
- BTN and BB calls, any other nonzero cold calls, overcalls, and squeezes;
- SB completes and BB raises in the unopened blind-versus-blind tree;
- calls and later raises after a 3-bet or 4-bet, including 5-bet all-ins;
- heads-up and multiway postflop continuation values for every preflop terminal
  used by the solve; and
- the approved no-flop-no-drop rake and cap at settlement.

The source may use a validated and disclosed value model for expensive
postflop continuations. It may not silently award multiway pots by raw equity,
force all players to check down, or pretend players behind Hero have already
folded. Any approximation must be versioned and pass the P2.13-P2.18 accuracy
and disclosure gates.

## Explicitly deferred user-facing drills

- limped pots other than the unopened SB's complete alternative;
- isolation raises;
- open plus cold call: overcall or squeeze;
- open plus 3-bet: cold call or cold 4-bet;
- the 3-bettor facing a 4-bet;
- direct multiway postflop study; and
- alternate open, 3-bet, and 4-bet sizings.

These are roadmap extensions, not evidence that the underlying actions are
necessarily exploitable.

## Acceptance checks

P2.11 remains satisfied only if subsequent implementation preserves all of the
following:

1. all 35 scenario families are selectable in Study and Trainer;
2. position order and the visible action history are canonical and complete;
3. every displayed action uses the exact target and all-in metadata from the
   solution artifact;
4. all grouped strategies retain exact-combo drill and history data;
5. source metadata distinguishes exposed study nodes from hidden computational
   support; and
6. unsupported scenario families are absent rather than silently mapped to a
   nearby tree.

## Decision rationale

Rake and no-flop-no-drop make passive entry less attractive, so RFI,
versus-open, and versus-3-bet decisions provide the best first learning return
for this cash preset. That does not imply that optimal play produces no
multiway pots. The BTN can profitably cold-call in position, the BB receives a
discount and closes the action, and antes or unraked play can make calling much
more attractive.

The direct scope is therefore prioritized by frequency and learning value,
while the computation scope remains broad enough to avoid teaching ranges from
an artificial heads-up-only game.

## Supporting references

- [GTO Wizard: Cold-Calling in Straddle + Ante Games](https://blog.gtowizard.com/cold-calling-in-straddle-ante-games/)
- [GTO Wizard: Preflop Raise Sizing — Examining Rake and Position](https://blog.gtowizard.com/preflop-raise-sizing-examining-2-key-factors/)
- [donksolver 0.1.0 documentation and declared multiway limitations](https://pypi.org/project/donksolver/)
