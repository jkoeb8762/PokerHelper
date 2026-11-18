"""Strict validation for the versioned PokerHelper solution-artifact format."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from pokerhelper.domain.canonical import content_id
from pokerhelper.domain.cards import ExactCombo, all_exact_combos
from pokerhelper.domain.errors import DomainError, fail


SCHEMA_VERSION = "1.0.0"
FREQUENCY_TOLERANCE = Decimal("0.000000001")
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_NODE_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 100 * 1024 * 1024
MAX_NODES = 256
_PLAIN_DECIMAL = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_NODE_ID = re.compile(r"^node-[0-9]{3}$")
_ALLOWED_AUTHORIZATION = {"SELF_GENERATED", "LICENSED", "PUBLIC_DOMAIN", "OPEN_SOURCE"}
_ALLOWED_ACTION_TYPES = {"FOLD", "CHECK", "CALL", "RAISE_TO"}


@dataclass(frozen=True, slots=True)
class SolutionArtifact:
    """A fully validated artifact rooted at ``path``."""

    path: Path
    manifest: dict[str, Any]
    nodes: dict[str, dict[str, Any]]

    @property
    def solution_id(self) -> str:
        return str(self.manifest["solutionId"])

    @property
    def scenario(self) -> dict[str, Any]:
        return dict(self.manifest["scenario"])

    def node(self, node_id: str) -> dict[str, Any]:
        try:
            return self.nodes[node_id]
        except KeyError:
            fail(
                "SOLUTION_NODE_NOT_FOUND",
                "nodeId",
                "The requested node does not exist in this solution.",
                details={"nodeId": node_id, "solutionId": self.solution_id},
            )

    @classmethod
    def load(cls, path: str | Path) -> "SolutionArtifact":
        root = Path(path).resolve()
        manifest_path = root / "manifest.json"
        manifest = _read_json(manifest_path, MAX_MANIFEST_BYTES, "manifest")
        _validate_manifest(manifest)

        expected_paths = {"manifest.json", *(reference["path"] for reference in manifest["nodes"])}
        actual_paths: set[str] = set()
        for item in root.rglob("*"):
            if item.is_symlink():
                fail("SOLUTION_SYMLINK_FORBIDDEN", "artifact", "Solution artifacts cannot contain symbolic links.")
            if item.is_file():
                actual_paths.add(item.relative_to(root).as_posix())
        if actual_paths != expected_paths:
            fail(
                "SOLUTION_FILE_SET_INVALID",
                "artifact",
                "The artifact contains missing or unreferenced files.",
                details={"missing": sorted(expected_paths - actual_paths), "unexpected": sorted(actual_paths - expected_paths)},
            )

        total_bytes = manifest_path.stat().st_size
        nodes: dict[str, dict[str, Any]] = {}
        node_refs = manifest["nodes"]
        if len(node_refs) > MAX_NODES:
            fail("SOLUTION_TOO_MANY_NODES", "manifest.nodes", "The artifact exceeds the node limit.")

        for index, reference in enumerate(node_refs):
            node_id = reference["nodeId"]
            relative = Path(reference["path"])
            node_path = (root / relative).resolve()
            if root not in node_path.parents or node_path == root:
                fail(
                    "SOLUTION_PATH_ESCAPE",
                    f"manifest.nodes[{index}].path",
                    "Node paths must remain inside the artifact directory.",
                )
            raw = _read_bytes(node_path, MAX_NODE_BYTES, f"nodes.{node_id}")
            total_bytes += len(raw)
            if total_bytes > MAX_ARTIFACT_BYTES:
                fail("SOLUTION_ARTIFACT_TOO_LARGE", "manifest.nodes", "The artifact exceeds the size limit.")
            digest = hashlib.sha256(raw).hexdigest()
            if digest != reference["sha256"]:
                fail(
                    "SOLUTION_NODE_HASH_MISMATCH",
                    f"manifest.nodes[{index}].sha256",
                    "A node file does not match its declared SHA-256 digest.",
                    details={"nodeId": node_id, "expected": reference["sha256"], "actual": digest},
                )
            try:
                node = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                fail("SOLUTION_JSON_INVALID", f"nodes.{node_id}", "A node file is not valid UTF-8 JSON.", details={"reason": str(exc)})
            _validate_node(node, node_id, manifest)
            if node_id in nodes:
                fail("SOLUTION_NODE_DUPLICATE", "manifest.nodes", "Node identifiers must be unique.", details={"nodeId": node_id})
            nodes[node_id] = node

        referenced_ids = {item["nodeId"] for item in node_refs}
        root_id = manifest["scenario"]["rootNodeId"]
        if root_id not in referenced_ids:
            fail("SOLUTION_ROOT_NODE_MISSING", "manifest.scenario.rootNodeId", "The scenario root node is absent.")
        for node_id, node in nodes.items():
            for action_id, child_id in node["childNodeByAction"].items():
                if child_id not in referenced_ids:
                    fail(
                        "SOLUTION_CHILD_NODE_MISSING",
                        f"nodes.{node_id}.childNodeByAction.{action_id}",
                        "A child decision node is absent from the artifact.",
                        details={"childNodeId": child_id},
                    )

        expected_id = _solution_id(manifest)
        if manifest["solutionId"] != expected_id:
            fail(
                "SOLUTION_ID_MISMATCH",
                "manifest.solutionId",
                "The solution identifier does not match its canonical metadata and node hashes.",
                details={"expected": expected_id, "actual": manifest["solutionId"]},
            )
        return cls(root, manifest, nodes)


def _read_bytes(path: Path, limit: int, logical_path: str) -> bytes:
    try:
        size = path.stat().st_size
    except OSError as exc:
        fail("SOLUTION_FILE_MISSING", logical_path, "A required artifact file is missing.", details={"reason": str(exc)})
    if size > limit:
        fail("SOLUTION_FILE_TOO_LARGE", logical_path, "An artifact file exceeds its size limit.", details={"bytes": size, "limit": limit})
    try:
        return path.read_bytes()
    except OSError as exc:
        fail("SOLUTION_FILE_UNREADABLE", logical_path, "A required artifact file cannot be read.", details={"reason": str(exc)})


def _read_json(path: Path, limit: int, logical_path: str) -> dict[str, Any]:
    raw = _read_bytes(path, limit, logical_path)
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail("SOLUTION_JSON_INVALID", logical_path, "The artifact file is not valid UTF-8 JSON.", details={"reason": str(exc)})
    if not isinstance(value, dict):
        fail("SOLUTION_OBJECT_REQUIRED", logical_path, "The artifact file must contain a JSON object.")
    return value


def _require_object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        fail("SOLUTION_OBJECT_REQUIRED", path, "Expected a JSON object.")
    return value


def _require_keys(value: Mapping[str, Any], required: set[str], path: str, *, exact: bool = True) -> None:
    missing = sorted(required - set(value))
    if missing:
        fail("SOLUTION_FIELD_MISSING", path, "Required artifact fields are missing.", details={"fields": missing})
    if exact:
        extra = sorted(set(value) - required)
        if extra:
            fail("SOLUTION_FIELD_UNKNOWN", path, "Unknown fields are not allowed by this schema version.", details={"fields": extra})


def _decimal(value: Any, path: str) -> Decimal:
    if not isinstance(value, str) or not _PLAIN_DECIMAL.fullmatch(value):
        fail("SOLUTION_DECIMAL_INVALID", path, "Canonical solution decimals must be plain JSON strings.", details={"received": value})
    try:
        result = Decimal(value)
    except InvalidOperation:
        fail("SOLUTION_DECIMAL_INVALID", path, "Expected a finite plain decimal string.")
    if not result.is_finite():
        fail("SOLUTION_DECIMAL_INVALID", path, "NaN and infinity are forbidden.")
    return result


def _validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schemaVersion", "identityProfileVersion", "solutionId", "version", "title",
        "generatedAt", "authorization", "source", "game", "tree", "solver",
        "accuracy", "limitations", "trainerEligible", "scenario", "nodes",
    }
    _require_keys(manifest, required, "manifest")
    if manifest["schemaVersion"] != SCHEMA_VERSION:
        fail("SOLUTION_SCHEMA_UNSUPPORTED", "manifest.schemaVersion", "This solution schema version is not supported.", details={"received": manifest["schemaVersion"]})
    if manifest["identityProfileVersion"] != "1":
        fail("SOLUTION_IDENTITY_PROFILE_UNSUPPORTED", "manifest.identityProfileVersion", "This identity profile is not supported.")
    if not isinstance(manifest["nodes"], list) or not manifest["nodes"]:
        fail("SOLUTION_NODES_REQUIRED", "manifest.nodes", "At least one solution node is required.")
    if not isinstance(manifest["limitations"], list) or not all(isinstance(item, str) and item for item in manifest["limitations"]):
        fail("SOLUTION_LIMITATIONS_INVALID", "manifest.limitations", "Limitations must be a non-empty-string list.")
    if not isinstance(manifest["trainerEligible"], bool):
        fail("SOLUTION_TRAINER_ELIGIBILITY_INVALID", "manifest.trainerEligible", "Trainer eligibility must be boolean.")

    authorization = _require_object(manifest["authorization"], "manifest.authorization")
    _require_keys(authorization, {"basis", "license", "licenseUrl", "redistributionPermitted"}, "manifest.authorization")
    if authorization["basis"] not in _ALLOWED_AUTHORIZATION:
        fail("SOLUTION_AUTHORIZATION_INVALID", "manifest.authorization.basis", "The authorization basis is unsupported.")
    if authorization["redistributionPermitted"] is not True:
        fail("SOLUTION_REDISTRIBUTION_FORBIDDEN", "manifest.authorization.redistributionPermitted", "Bundled artifacts must permit redistribution.")

    source = _require_object(manifest["source"], "manifest.source")
    _require_keys(source, {"name", "owner", "repository", "commit", "generationMethod"}, "manifest.source")
    if not isinstance(source["commit"], str) or not _GIT_COMMIT.fullmatch(source["commit"]):
        fail("SOLUTION_SOURCE_COMMIT_INVALID", "manifest.source.commit", "The source commit must be a full lowercase Git object identifier.")

    game = _require_object(manifest["game"], "manifest.game")
    _require_keys(game, {"variant", "format", "tableSize", "effectiveStackBb", "smallBlindBb", "bigBlindBb", "anteBb", "positions", "rake"}, "manifest.game")
    for key in ("effectiveStackBb", "smallBlindBb", "bigBlindBb", "anteBb"):
        _decimal(game[key], f"manifest.game.{key}")
    rake = _require_object(game["rake"], "manifest.game.rake")
    _require_keys(rake, {"policyVersion", "rate", "capBb", "noFlopNoDrop"}, "manifest.game.rake")
    _decimal(rake["rate"], "manifest.game.rake.rate")
    _decimal(rake["capBb"], "manifest.game.rake.capBb")

    tree = _require_object(manifest["tree"], "manifest.tree")
    _require_keys(tree, {"allowLimp", "openRaiseToBb", "reraisePotFractions", "maxRaises", "includeAllIn"}, "manifest.tree")
    if not isinstance(tree["openRaiseToBb"], list) or not isinstance(tree["reraisePotFractions"], list):
        fail("SOLUTION_TREE_SIZING_INVALID", "manifest.tree", "Tree sizings must be lists.")
    for index, item in enumerate(tree["openRaiseToBb"]):
        _decimal(item, f"manifest.tree.openRaiseToBb[{index}]")
    for index, item in enumerate(tree["reraisePotFractions"]):
        _decimal(item, f"manifest.tree.reraisePotFractions[{index}]")

    solver = _require_object(manifest["solver"], "manifest.solver")
    _require_keys(
        solver,
        {"algorithm", "iterations", "equitySamplesPerCanonicalMatchup", "equitySeed", "realizeIp", "realizeOop", "evBaseline"},
        "manifest.solver",
    )
    for key in ("iterations", "equitySamplesPerCanonicalMatchup", "equitySeed"):
        if not isinstance(solver[key], int) or isinstance(solver[key], bool) or solver[key] < 0:
            fail("SOLUTION_SOLVER_INTEGER_INVALID", f"manifest.solver.{key}", "Solver counts and seeds must be non-negative integers.")
    _decimal(solver["realizeIp"], "manifest.solver.realizeIp")
    _decimal(solver["realizeOop"], "manifest.solver.realizeOop")

    accuracy = _require_object(manifest["accuracy"], "manifest.accuracy")
    _require_keys(accuracy, {"frequencyAbsTolerance", "evAbsToleranceBb", "exploitabilityBbPerHand", "modelAccuracyBoundBb", "extractionMaxFrequencyError", "extractionMaxEvErrorBb"}, "manifest.accuracy")
    _decimal(accuracy["frequencyAbsTolerance"], "manifest.accuracy.frequencyAbsTolerance")
    _decimal(accuracy["evAbsToleranceBb"], "manifest.accuracy.evAbsToleranceBb")
    _decimal(accuracy["exploitabilityBbPerHand"], "manifest.accuracy.exploitabilityBbPerHand")
    if accuracy["modelAccuracyBoundBb"] is not None:
        model_bound = _decimal(accuracy["modelAccuracyBoundBb"], "manifest.accuracy.modelAccuracyBoundBb")
    else:
        model_bound = None
    _decimal(accuracy["extractionMaxFrequencyError"], "manifest.accuracy.extractionMaxFrequencyError")
    _decimal(accuracy["extractionMaxEvErrorBb"], "manifest.accuracy.extractionMaxEvErrorBb")
    if manifest["trainerEligible"] and (model_bound is None or model_bound > Decimal("0.001")):
        fail(
            "SOLUTION_TRAINER_ACCURACY_INSUFFICIENT",
            "manifest.trainerEligible",
            "Trainer grading requires a declared absolute model-accuracy bound of at most 0.001 BB.",
        )

    scenario = _require_object(manifest["scenario"], "manifest.scenario")
    _require_keys(scenario, {"scenarioId", "title", "description", "rootNodeId", "assumedPriorActions"}, "manifest.scenario")
    if not isinstance(scenario["assumedPriorActions"], list):
        fail("SOLUTION_PRIOR_ACTIONS_INVALID", "manifest.scenario.assumedPriorActions", "Prior actions must be a list.")

    seen: set[str] = set()
    for index, item in enumerate(manifest["nodes"]):
        reference = _require_object(item, f"manifest.nodes[{index}]")
        _require_keys(reference, {"nodeId", "path", "sha256"}, f"manifest.nodes[{index}]")
        node_id = reference["nodeId"]
        if not isinstance(node_id, str) or not _NODE_ID.fullmatch(node_id):
            fail("SOLUTION_NODE_ID_INVALID", f"manifest.nodes[{index}].nodeId", "Node IDs must match node-NNN.")
        if node_id in seen:
            fail("SOLUTION_NODE_DUPLICATE", "manifest.nodes", "Node identifiers must be unique.", details={"nodeId": node_id})
        seen.add(node_id)
        if reference["path"] != f"nodes/{node_id}.json":
            fail("SOLUTION_NODE_PATH_INVALID", f"manifest.nodes[{index}].path", "Node paths must use the canonical nodes/<nodeId>.json form.")
        if not isinstance(reference["sha256"], str) or not _SHA256.fullmatch(reference["sha256"]):
            fail("SOLUTION_NODE_HASH_INVALID", f"manifest.nodes[{index}].sha256", "Node SHA-256 must be 64 lowercase hexadecimal characters.")


def _validate_node(node: Any, expected_node_id: str, manifest: Mapping[str, Any]) -> None:
    if not isinstance(node, dict):
        fail("SOLUTION_OBJECT_REQUIRED", f"nodes.{expected_node_id}", "A node must be a JSON object.")
    required = {
        "schemaVersion", "nodeId", "sourceNodeIndex", "actor", "actionHistory", "potBb",
        "actorContributionBb", "actorStackBehindBb", "amountToCallBb", "actions",
        "childNodeByAction", "groupedHands", "exactCombos",
    }
    path = f"nodes.{expected_node_id}"
    _require_keys(node, required, path)
    if node["schemaVersion"] != SCHEMA_VERSION or node["nodeId"] != expected_node_id:
        fail("SOLUTION_NODE_ID_MISMATCH", f"{path}.nodeId", "The node body does not match its manifest reference.")
    if node["actor"] not in {"SB", "BB"}:
        fail("SOLUTION_ACTOR_INVALID", f"{path}.actor", "Only SB and BB are supported by this artifact.")
    if not isinstance(node["actionHistory"], list):
        fail("SOLUTION_ACTION_HISTORY_INVALID", f"{path}.actionHistory", "Action history must be a list.")
    for index, item in enumerate(node["actionHistory"]):
        history = _require_object(item, f"{path}.actionHistory[{index}]")
        _require_keys(history, {"actor", "type", "targetBb", "isAllIn", "label"}, f"{path}.actionHistory[{index}]")
        if history["actor"] not in {"SB", "BB"} or history["type"] not in _ALLOWED_ACTION_TYPES:
            fail("SOLUTION_ACTION_HISTORY_INVALID", f"{path}.actionHistory[{index}]", "History actor or action type is invalid.")
        _validate_action_shape(history, f"{path}.actionHistory[{index}]")

    numeric_context = {
        key: _decimal(node[key], f"{path}.{key}")
        for key in ("potBb", "actorContributionBb", "actorStackBehindBb", "amountToCallBb")
    }
    if any(value < 0 for value in numeric_context.values()):
        fail("SOLUTION_NODE_AMOUNT_NEGATIVE", path, "Pot, contribution, stack, and call amounts cannot be negative.")

    actions = node["actions"]
    if not isinstance(actions, list) or not actions:
        fail("SOLUTION_ACTIONS_REQUIRED", f"{path}.actions", "A decision node needs at least one action.")
    action_ids: list[str] = []
    for index, item in enumerate(actions):
        action = _require_object(item, f"{path}.actions[{index}]")
        _require_keys(action, {"actionId", "type", "label", "targetBb", "isAllIn", "sourceCode"}, f"{path}.actions[{index}]")
        if action["type"] not in _ALLOWED_ACTION_TYPES:
            fail("SOLUTION_ACTION_TYPE_INVALID", f"{path}.actions[{index}].type", "The action type is not supported.")
        if not isinstance(action["isAllIn"], bool):
            fail("SOLUTION_ACTION_ALL_IN_INVALID", f"{path}.actions[{index}].isAllIn", "isAllIn must be boolean.")
        _validate_action_shape(action, f"{path}.actions[{index}]")
        action_id = action["actionId"]
        if not isinstance(action_id, str) or not action_id or action_id in action_ids:
            fail("SOLUTION_ACTION_ID_INVALID", f"{path}.actions[{index}].actionId", "Action IDs must be non-empty and unique.")
        action_ids.append(action_id)

    children = _require_object(node["childNodeByAction"], f"{path}.childNodeByAction")
    if not set(children).issubset(action_ids):
        fail("SOLUTION_CHILD_ACTION_INVALID", f"{path}.childNodeByAction", "Child mappings may only use declared action IDs.")
    if not all(isinstance(value, str) and _NODE_ID.fullmatch(value) for value in children.values()):
        fail("SOLUTION_CHILD_NODE_ID_INVALID", f"{path}.childNodeByAction", "Child node IDs must match node-NNN.")

    exact = _require_object(node["exactCombos"], f"{path}.exactCombos")
    expected_combos = {str(combo) for combo in all_exact_combos()}
    if set(exact) != expected_combos:
        fail(
            "SOLUTION_COMBO_SET_INVALID",
            f"{path}.exactCombos",
            "Every node must contain each of the 1,326 possible exact combos exactly once.",
            details={"missingCount": len(expected_combos - set(exact)), "extraCount": len(set(exact) - expected_combos)},
        )

    grouped_expected: dict[str, list[tuple[Decimal, dict[str, Decimal], dict[str, Decimal]]]] = {}
    for combo_text, raw_strategy in exact.items():
        combo = ExactCombo.parse(combo_text, path=f"{path}.exactCombos.{combo_text}")
        strategy = _require_object(raw_strategy, f"{path}.exactCombos.{combo_text}")
        _require_keys(strategy, {"group", "reachFrequency", "frequencies", "evBb"}, f"{path}.exactCombos.{combo_text}")
        if strategy["group"] != combo.grouped_class:
            fail("SOLUTION_COMBO_GROUP_MISMATCH", f"{path}.exactCombos.{combo_text}.group", "Exact combo and grouped hand disagree.")
        reach = _decimal(strategy["reachFrequency"], f"{path}.exactCombos.{combo_text}.reachFrequency")
        if reach < 0 or reach > 1:
            fail("SOLUTION_REACH_OUT_OF_RANGE", f"{path}.exactCombos.{combo_text}.reachFrequency", "Reach frequency must be between zero and one.")
        frequencies = _strategy_map(strategy["frequencies"], action_ids, f"{path}.exactCombos.{combo_text}.frequencies", frequency=True)
        evs = _strategy_map(strategy["evBb"], action_ids, f"{path}.exactCombos.{combo_text}.evBb", frequency=False)
        total = sum(frequencies.values(), Decimal(0))
        if abs(total - Decimal(1)) > FREQUENCY_TOLERANCE:
            fail("SOLUTION_FREQUENCY_NOT_NORMALIZED", f"{path}.exactCombos.{combo_text}.frequencies", "Action frequencies must sum to one.", details={"sum": str(total)})
        grouped_expected.setdefault(combo.grouped_class, []).append((reach, frequencies, evs))

    grouped = _require_object(node["groupedHands"], f"{path}.groupedHands")
    if set(grouped) != set(grouped_expected) or len(grouped) != 169:
        fail("SOLUTION_GROUP_SET_INVALID", f"{path}.groupedHands", "Every node must contain all 169 grouped starting hands.")
    tolerance = _decimal(manifest["accuracy"]["frequencyAbsTolerance"], "manifest.accuracy.frequencyAbsTolerance")
    ev_tolerance = _decimal(manifest["accuracy"]["evAbsToleranceBb"], "manifest.accuracy.evAbsToleranceBb")
    for group, members in grouped_expected.items():
        raw_group = _require_object(grouped[group], f"{path}.groupedHands.{group}")
        _require_keys(raw_group, {"comboCount", "reachWeight", "frequencies", "evBb"}, f"{path}.groupedHands.{group}")
        if raw_group["comboCount"] != len(members):
            fail("SOLUTION_GROUP_COMBO_COUNT_INVALID", f"{path}.groupedHands.{group}.comboCount", "Grouped combo count is incorrect.")
        declared_reach = _decimal(raw_group["reachWeight"], f"{path}.groupedHands.{group}.reachWeight")
        weight = sum((member[0] for member in members), Decimal(0))
        if abs(declared_reach - weight) > tolerance:
            fail("SOLUTION_GROUP_REACH_MISMATCH", f"{path}.groupedHands.{group}.reachWeight", "Grouped reach does not match exact combos.")
        declared_freq = _strategy_map(raw_group["frequencies"], action_ids, f"{path}.groupedHands.{group}.frequencies", frequency=True)
        declared_evs = _strategy_map(raw_group["evBb"], action_ids, f"{path}.groupedHands.{group}.evBb", frequency=False)
        divisor = weight if weight > 0 else Decimal(len(members))
        for action_id in action_ids:
            if weight > 0:
                expected_frequency = sum((reach * freq[action_id] for reach, freq, _ in members), Decimal(0)) / divisor
                expected_ev = sum((reach * ev[action_id] for reach, _, ev in members), Decimal(0)) / divisor
            else:
                expected_frequency = sum((freq[action_id] for _, freq, _ in members), Decimal(0)) / divisor
                expected_ev = sum((ev[action_id] for _, _, ev in members), Decimal(0)) / divisor
            if abs(declared_freq[action_id] - expected_frequency) > tolerance:
                fail("SOLUTION_GROUP_FREQUENCY_MISMATCH", f"{path}.groupedHands.{group}.frequencies.{action_id}", "Grouped frequency does not match exact-combo weighting.")
            if abs(declared_evs[action_id] - expected_ev) > ev_tolerance:
                fail("SOLUTION_GROUP_EV_MISMATCH", f"{path}.groupedHands.{group}.evBb.{action_id}", "Grouped EV does not match exact-combo weighting.")


def _strategy_map(value: Any, action_ids: list[str], path: str, *, frequency: bool) -> dict[str, Decimal]:
    mapping = _require_object(value, path)
    if set(mapping) != set(action_ids):
        fail("SOLUTION_ACTION_SET_MISMATCH", path, "Every supported action must have exactly one value.")
    result = {action_id: _decimal(mapping[action_id], f"{path}.{action_id}") for action_id in action_ids}
    if frequency and any(number < 0 or number > 1 for number in result.values()):
        fail("SOLUTION_FREQUENCY_OUT_OF_RANGE", path, "Action frequencies must be between zero and one.")
    return result


def _validate_action_shape(action: Mapping[str, Any], path: str) -> None:
    action_type = action["type"]
    target = action["targetBb"]
    if action_type == "RAISE_TO":
        if target is None or _decimal(target, f"{path}.targetBb") <= 0:
            fail("SOLUTION_RAISE_TARGET_INVALID", f"{path}.targetBb", "A raise-to action requires a positive target in BB.")
    elif target is not None:
        fail("SOLUTION_ACTION_TARGET_FORBIDDEN", f"{path}.targetBb", "Only raise-to actions may carry a target.")
    if action["isAllIn"] and action_type not in {"CALL", "RAISE_TO"}:
        fail("SOLUTION_ACTION_ALL_IN_INVALID", f"{path}.isAllIn", "Only calls and raises may be all-in.")


def _solution_id(manifest: Mapping[str, Any]) -> str:
    payload = dict(manifest)
    payload.pop("solutionId", None)
    return content_id("solution", payload)


def solution_id_for_manifest(manifest: Mapping[str, Any]) -> str:
    """Public helper used by deterministic artifact generators."""

    return _solution_id(manifest)


def validation_error_payload(exc: DomainError) -> dict[str, Any]:
    return {"error": exc.to_dict()}
