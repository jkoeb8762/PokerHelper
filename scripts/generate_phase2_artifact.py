"""Generate the authorized Phase 2 reference pack from pinned poker-solver source.

This is a maintainer tool, not an application runtime dependency. It deliberately
imports the solver from a checked-out source directory so the exact Git commit can
be verified before generation.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np


PINNED_COMMIT = "6d54d3725c50d5e74c8971723a616eb52d664f3c"
SCHEMA_VERSION = "1.0.0"
RANK_ORDER = "AKQJT98765432"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--generated-at", default="2026-11-18T00:00:00-08:00")
    parser.add_argument("--equity-samples", type=int, default=8000)
    parser.add_argument("--equity-seed", type=int, default=1)
    parser.add_argument("--equity-workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--iterations", type=int, default=800)
    parser.add_argument("--realize-ip", type=float, default=1.0)
    parser.add_argument("--realize-oop", type=float, default=0.85)
    return parser.parse_args()


def _git_head(source_root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
    ).strip()


def _fmt(value: float | Decimal, places: int = 12) -> str:
    number = Decimal(str(value)) if not isinstance(value, Decimal) else value
    quantizer = Decimal(1).scaleb(-places)
    number = number.quantize(quantizer)
    if number == 0:
        return "0"
    text = format(number, "f").rstrip("0").rstrip(".")
    return text


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _group_order() -> list[str]:
    groups: list[str] = []
    for row, first in enumerate(RANK_ORDER):
        for column, second in enumerate(RANK_ORDER):
            if row == column:
                groups.append(first + second)
            elif column > row:
                groups.append(first + second + "s")
            else:
                groups.append(second + first + "o")
    return groups


def _action(action_code: str, stack: float, *, facing: bool, actor: str, is_root: bool) -> dict[str, Any]:
    if action_code == "F":
        return {"actionId": "fold", "type": "FOLD", "label": "Fold", "targetBb": None, "isAllIn": False, "sourceCode": action_code}
    if action_code == "X":
        return {"actionId": "check", "type": "CHECK", "label": "Check", "targetBb": None, "isAllIn": False, "sourceCode": action_code}
    if action_code == "C":
        label = "Limp to 1 BB" if is_root and actor == "SB" else "Call"
        return {"actionId": "call", "type": "CALL", "label": label, "targetBb": None, "isAllIn": False, "sourceCode": action_code}
    if action_code == "A":
        target = _fmt(stack, 4)
        return {"actionId": "all-in", "type": "RAISE_TO", "label": f"All-in to {target} BB", "targetBb": target, "isAllIn": True, "sourceCode": action_code}
    if action_code.startswith("R"):
        target = _fmt(float(action_code[1:]), 4)
        return {"actionId": f"raise-to-{target}", "type": "RAISE_TO", "label": f"Raise to {target} BB", "targetBb": target, "isAllIn": False, "sourceCode": action_code}
    raise ValueError(f"unsupported source action {action_code!r}")


def _history_record(action: dict[str, Any], actor: str) -> dict[str, Any]:
    return {
        "actor": actor,
        "type": action["type"],
        "targetBb": action["targetBb"],
        "isAllIn": action["isAllIn"],
        "label": action["label"],
    }


def _collect_states(tree: Any, stack: float) -> dict[int, dict[str, Any]]:
    states: dict[int, dict[str, Any]] = {}

    def visit(index: int, c0: float, c1: float, history: list[dict[str, Any]]) -> None:
        node = tree.nodes[index]
        if node.kind != "decision":
            return
        existing = states.get(index)
        state = {"c0": c0, "c1": c1, "history": history}
        if existing is not None:
            if existing != state:
                raise RuntimeError(f"public node {index} reached through conflicting states")
            return
        states[index] = state
        current = max(c0, c1)
        actor_contribution = c0 if node.player == 0 else c1
        facing = current - actor_contribution > 1e-9
        actor = "SB" if node.player == 0 else "BB"
        for source_code, child_index in zip(node.actions, node.children):
            child = tree.nodes[child_index]
            if child.kind != "decision":
                continue
            action = _action(source_code, stack, facing=facing, actor=actor, is_root=index == tree.root)
            nc0, nc1 = c0, c1
            if source_code == "C":
                if node.player == 0:
                    nc0 = current
                else:
                    nc1 = current
            elif source_code.startswith("R"):
                target = float(source_code[1:])
                if node.player == 0:
                    nc0 = target
                else:
                    nc1 = target
            elif source_code == "A":
                if node.player == 0:
                    nc0 = stack
                else:
                    nc1 = stack
            visit(child_index, nc0, nc1, history + [_history_record(action, actor)])

    visit(tree.root, float(tree.cfg.sb), float(tree.cfg.bb), [])
    return states


def _source_combo_to_canonical(text: str, ExactCombo: Any) -> str:
    return str(ExactCombo.parse(text))


def _policy_value(solver: Any, index: int, opponent_reach: Any, hero: int) -> Any:
    """Counterfactual value vector when both players follow average strategy."""

    node = solver.tree.nodes[index]
    if node.kind == "terminal":
        return solver._terminal_v0(node, opponent_reach) if hero == 0 else solver._terminal_v1(node, opponent_reach)
    sigma = solver.average_strategy(index)
    total = solver.xp.zeros(len(sigma), dtype=solver.xp.float64)
    for action_index, child in enumerate(node.children):
        if node.player == hero:
            total += sigma[:, action_index] * _policy_value(solver, child, opponent_reach, hero)
        else:
            total += _policy_value(solver, child, opponent_reach * sigma[:, action_index], hero)
    return total


def _action_evs(solver: Any, node_index: int, opponent_reach: Any, prior_contribution: float, to_cpu: Any) -> np.ndarray:
    node = solver.tree.nodes[node_index]
    denominator = to_cpu(solver.COMPAT @ opponent_reach).astype(np.float64)
    values: list[np.ndarray] = []
    for child in node.children:
        numerator = to_cpu(_policy_value(solver, child, opponent_reach, node.player)).astype(np.float64)
        conditional = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)
        values.append(conditional + prior_contribution)
    return np.stack(values, axis=1)


def _build_node(
    solver: Any,
    node_index: int,
    state: dict[str, Any],
    ExactCombo: Any,
    combo_str: Any,
    COMBO_CANON: list[int],
    CANON: list[Any],
    to_cpu: Any,
) -> tuple[dict[str, Any], float, float]:
    node = solver.tree.nodes[node_index]
    actor = "SB" if node.player == 0 else "BB"
    contribution = state["c0"] if node.player == 0 else state["c1"]
    current = max(state["c0"], state["c1"])
    facing = current - contribution > 1e-9
    actions = [_action(code, solver.cfg.stack, facing=facing, actor=actor, is_root=node_index == solver.tree.root) for code in node.actions]
    action_ids = [action["actionId"] for action in actions]
    r0, r1 = solver._reach_to_node(node_index)
    own_reach = to_cpu(r0 if node.player == 0 else r1).astype(np.float64)
    opponent_reach = r1 if node.player == 0 else r0
    sigma = to_cpu(solver.average_strategy(node_index)).astype(np.float64)
    evs = _action_evs(solver, node_index, opponent_reach, contribution, to_cpu)

    exact: dict[str, dict[str, Any]] = {}
    members: dict[str, list[str]] = defaultdict(list)
    max_frequency_error = 0.0
    max_ev_error = 0.0
    for combo_index in range(len(sigma)):
        combo = _source_combo_to_canonical(combo_str(combo_index), ExactCombo)
        group = ExactCombo.parse(combo).grouped_class
        reach_text = _fmt(own_reach[combo_index])
        frequency_text = {action_id: _fmt(sigma[combo_index, action_index]) for action_index, action_id in enumerate(action_ids)}
        ev_text = {action_id: _fmt(evs[combo_index, action_index]) for action_index, action_id in enumerate(action_ids)}
        for action_index, action_id in enumerate(action_ids):
            max_frequency_error = max(max_frequency_error, abs(float(Decimal(frequency_text[action_id])) - sigma[combo_index, action_index]))
            max_ev_error = max(max_ev_error, abs(float(Decimal(ev_text[action_id])) - evs[combo_index, action_index]))
        exact[combo] = {"group": group, "reachFrequency": reach_text, "frequencies": frequency_text, "evBb": ev_text}
        members[group].append(combo)

    grouped: dict[str, dict[str, Any]] = {}
    for group in _group_order():
        combos = members[group]
        weights = [Decimal(exact[combo]["reachFrequency"]) for combo in combos]
        total_weight = sum(weights, Decimal(0))
        divisor = total_weight if total_weight > 0 else Decimal(len(combos))
        frequencies: dict[str, str] = {}
        grouped_evs: dict[str, str] = {}
        for action_id in action_ids:
            if total_weight > 0:
                frequency = sum((weight * Decimal(exact[combo]["frequencies"][action_id]) for combo, weight in zip(combos, weights)), Decimal(0)) / divisor
                ev = sum((weight * Decimal(exact[combo]["evBb"][action_id]) for combo, weight in zip(combos, weights)), Decimal(0)) / divisor
            else:
                frequency = sum((Decimal(exact[combo]["frequencies"][action_id]) for combo in combos), Decimal(0)) / divisor
                ev = sum((Decimal(exact[combo]["evBb"][action_id]) for combo in combos), Decimal(0)) / divisor
            frequencies[action_id] = _fmt(frequency)
            grouped_evs[action_id] = _fmt(ev)
        grouped[group] = {
            "comboCount": len(combos),
            "reachWeight": _fmt(total_weight),
            "frequencies": frequencies,
            "evBb": grouped_evs,
        }

    # Independent comparison against the source solver's own 169-hand extractor.
    _, source_grid, source_weights = solver.strategy_grid(node_index)
    for canon_index, canon in enumerate(CANON):
        record = grouped[canon.label]
        for action_index, action_id in enumerate(action_ids):
            max_frequency_error = max(max_frequency_error, abs(float(record["frequencies"][action_id]) - float(source_grid[canon_index, action_index])))
        max_frequency_error = max(max_frequency_error, abs(float(record["reachWeight"]) - float(source_weights[canon_index])))

    child_map: dict[str, str] = {}
    for action, child_index in zip(actions, node.children):
        if solver.tree.nodes[child_index].kind == "decision":
            child_map[action["actionId"]] = f"node-{child_index:03d}"

    body = {
        "schemaVersion": SCHEMA_VERSION,
        "nodeId": f"node-{node_index:03d}",
        "sourceNodeIndex": node_index,
        "actor": actor,
        "actionHistory": state["history"],
        "potBb": _fmt(state["c0"] + state["c1"], 4),
        "actorContributionBb": _fmt(contribution, 4),
        "actorStackBehindBb": _fmt(solver.cfg.stack - contribution, 4),
        "amountToCallBb": _fmt(current - contribution, 4),
        "actions": actions,
        "childNodeByAction": child_map,
        "groupedHands": grouped,
        "exactCombos": dict(sorted(exact.items())),
    }
    return body, max_frequency_error, max_ev_error


def main() -> int:
    args = _arguments()
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    actual_commit = _git_head(source_root)
    if actual_commit != PINNED_COMMIT:
        raise SystemExit(f"Refusing unpinned source: expected {PINNED_COMMIT}, received {actual_commit}")
    if args.equity_samples < 100 or args.iterations < 10:
        raise SystemExit("Production artifacts require at least 100 equity samples and 10 CFR+ iterations")

    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository_root / "backend" / "src"))
    sys.path.insert(0, str(source_root / "src"))
    os.environ.setdefault("POKER_SOLVER_CACHE", str(repository_root / ".cache" / "poker-solver"))

    from pokerhelper.domain.cards import ExactCombo
    from pokerhelper.solutions.artifact import SolutionArtifact, solution_id_for_manifest
    from poker_solver import BetConfig, PreflopSolver
    from poker_solver.backend import to_cpu
    from poker_solver.cards import CANON, COMBO_CANON, combo_str

    config = BetConfig(
        stack=100.0,
        sb=0.5,
        bb=1.0,
        allow_limp=True,
        open_sizes=(2.5,),
        reraise_pot_frac=(1.0,),
        max_raises=4,
        include_allin=True,
    )
    solver = PreflopSolver(
        config,
        equity_samples=args.equity_samples,
        equity_seed=args.equity_seed,
        verbose=True,
        device="cpu",
        equity_workers=args.equity_workers,
        realize_ip=args.realize_ip,
        realize_oop=args.realize_oop,
    )
    solver.solve(iterations=args.iterations, log_every=max(1, args.iterations // 4))
    exploitability = solver.exploitability()
    states = _collect_states(solver.tree, config.stack)

    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="phase2-artifact-", dir=output_root) as temporary:
        staging = Path(temporary)
        node_dir = staging / "nodes"
        node_dir.mkdir()
        references: list[dict[str, str]] = []
        max_frequency_error = 0.0
        max_ev_error = 0.0
        for node_index in solver.tree.decision_nodes:
            node, frequency_error, ev_error = _build_node(
                solver, node_index, states[node_index], ExactCombo, combo_str, COMBO_CANON, CANON, to_cpu
            )
            max_frequency_error = max(max_frequency_error, frequency_error)
            max_ev_error = max(max_ev_error, ev_error)
            node_id = node["nodeId"]
            raw = _json_bytes(node)
            relative = f"nodes/{node_id}.json"
            (staging / relative).write_bytes(raw)
            references.append({"nodeId": node_id, "path": relative, "sha256": hashlib.sha256(raw).hexdigest()})

        manifest: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "identityProfileVersion": "1",
            "solutionId": "",
            "version": "phase2-hu-sb-bb-100bb-v1",
            "title": "SB vs BB 100 BB reference strategy",
            "generatedAt": args.generated_at,
            "authorization": {
                "basis": "OPEN_SOURCE",
                "license": "MIT",
                "licenseUrl": "https://github.com/chirenonhive/poker-solver/blob/6d54d3725c50d5e74c8971723a616eb52d664f3c/LICENSE",
                "redistributionPermitted": True,
            },
            "source": {
                "name": "poker-solver",
                "owner": "poker-solver contributors",
                "repository": "https://github.com/chirenonhive/poker-solver",
                "commit": PINNED_COMMIT,
                "generationMethod": "Locally generated with exact-combo CFR+ and deterministic Monte Carlo equity seed",
            },
            "game": {
                "variant": "NLHE",
                "format": "CASH",
                "tableSize": 6,
                "effectiveStackBb": "100",
                "smallBlindBb": "0.5",
                "bigBlindBb": "1",
                "anteBb": "0",
                "positions": ["SB", "BB"],
                "rake": {"policyVersion": "NO_RAKE_SOURCE_V1", "rate": "0", "capBb": "0", "noFlopNoDrop": True},
            },
            "tree": {
                "allowLimp": True,
                "openRaiseToBb": ["2.5"],
                "reraisePotFractions": ["1"],
                "maxRaises": 4,
                "includeAllIn": True,
            },
            "solver": {
                "algorithm": "CFR+ with linear averaging",
                "iterations": args.iterations,
                "equitySamplesPerCanonicalMatchup": args.equity_samples,
                "equitySeed": args.equity_seed,
                "realizeIp": _fmt(args.realize_ip),
                "realizeOop": _fmt(args.realize_oop),
                "evBaseline": "Decision-point net EV in BB; chips committed before the decision are excluded",
            },
            "accuracy": {
                "frequencyAbsTolerance": "0.000000001",
                "evAbsToleranceBb": "0.000001",
                "exploitabilityBbPerHand": _fmt(exploitability),
                "modelAccuracyBoundBb": None,
                "extractionMaxFrequencyError": _fmt(max_frequency_error),
                "extractionMaxEvErrorBb": _fmt(max_ev_error),
            },
            "limitations": [
                "Heads-up SB-versus-BB decision tree after UTG, HJ, CO, and BTN fold; it is not a complete six-max solution.",
                "Flop-going leaves use a positional realized-equity heuristic rather than a solved postflop game.",
                "The source model is rake-free and does not implement the PokerHelper MVP cash-game rake preset.",
                "Monte Carlo equity sampling and finite CFR+ iterations add approximation error; no absolute game-accuracy bound is available.",
                "Study-only reference pack: it must not be used for Trainer EV-loss grading.",
            ],
            "trainerEligible": False,
            "scenario": {
                "scenarioId": "sb-vs-bb-100bb-after-folds",
                "title": "SB vs BB after folds",
                "description": "UTG, HJ, CO, and BTN fold; study every supported SB and BB preflop branch.",
                "rootNodeId": f"node-{solver.tree.root:03d}",
                "assumedPriorActions": [
                    {"actor": "UTG", "type": "FOLD"},
                    {"actor": "HJ", "type": "FOLD"},
                    {"actor": "CO", "type": "FOLD"},
                    {"actor": "BTN", "type": "FOLD"},
                ],
            },
            "nodes": references,
        }
        manifest["solutionId"] = solution_id_for_manifest(manifest)
        (staging / "manifest.json").write_bytes(_json_bytes(manifest))
        SolutionArtifact.load(staging)

        target = output_root / manifest["solutionId"].rsplit(":", 1)[-1]
        if target.exists():
            raise SystemExit(f"Refusing to overwrite existing immutable artifact: {target}")
        staging.rename(target)

    print(json.dumps({
        "solutionId": manifest["solutionId"],
        "path": str(target),
        "decisionNodes": len(references),
        "exploitabilityBbPerHand": manifest["accuracy"]["exploitabilityBbPerHand"],
        "extractionMaxFrequencyError": manifest["accuracy"]["extractionMaxFrequencyError"],
        "extractionMaxEvErrorBb": manifest["accuracy"]["extractionMaxEvErrorBb"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
