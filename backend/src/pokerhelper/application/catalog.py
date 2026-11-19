"""Read-only study catalog over validated immutable solution packs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pokerhelper.application.solution_rules import SolutionRuleValidator
from pokerhelper.domain.errors import fail
from pokerhelper.solutions import SolutionArtifact, SolutionStore


def bundled_solution_root() -> Path:
    return Path(__file__).resolve().parents[1] / "resources" / "solutions"


class StudyCatalog:
    def __init__(
        self,
        store: SolutionStore,
        seed_root: str | Path | None = None,
        rule_validator: SolutionRuleValidator | None = None,
    ) -> None:
        self.store = store
        self.seed_root = Path(seed_root).resolve() if seed_root is not None else bundled_solution_root()
        self.rule_validator = rule_validator or SolutionRuleValidator()

    def bootstrap(self) -> tuple[str, ...]:
        published: list[str] = []
        if self.seed_root.exists():
            for manifest in sorted(self.seed_root.glob("*/manifest.json")):
                result = self.store.publish(manifest.parent)
                self.rule_validator.validate_artifact(result.artifact)
                published.append(result.artifact.solution_id)
        self.store.write_index()
        return tuple(published)

    def scenarios(self) -> list[dict[str, Any]]:
        return [self._scenario_summary(artifact) for artifact in self.store.list()]

    def scenario(self, scenario_id: str) -> dict[str, Any]:
        artifact = self._artifact_for_scenario(scenario_id)
        manifest = artifact.manifest
        return {
            **self._scenario_summary(artifact),
            "description": manifest["scenario"]["description"],
            "assumedPriorActions": manifest["scenario"]["assumedPriorActions"],
            "tree": manifest["tree"],
            "nodes": [self._node_summary(artifact, reference["nodeId"]) for reference in manifest["nodes"]],
        }

    def node(self, solution_id: str, node_id: str) -> dict[str, Any]:
        artifact = self.store.get(solution_id)
        node = artifact.node(node_id)
        self.rule_validator.validate(artifact, node_id)
        return {
            "solutionId": solution_id,
            "solutionVersion": artifact.manifest["version"],
            "scenarioId": artifact.manifest["scenario"]["scenarioId"],
            **node,
        }

    def assumptions(self, solution_id: str) -> dict[str, Any]:
        artifact = self.store.get(solution_id)
        manifest = artifact.manifest
        return {
            "solutionId": solution_id,
            "version": manifest["version"],
            "generatedAt": manifest["generatedAt"],
            "authorization": manifest["authorization"],
            "source": manifest["source"],
            "game": manifest["game"],
            "tree": manifest["tree"],
            "solver": manifest["solver"],
            "accuracy": manifest["accuracy"],
            "limitations": manifest["limitations"],
            "trainerEligible": manifest["trainerEligible"],
            "practiceAvailable": True,
            "accuracyMode": "CERTIFIED" if manifest["trainerEligible"] else "REFERENCE_MODEL",
        }

    def _artifact_for_scenario(self, scenario_id: str) -> SolutionArtifact:
        for artifact in self.store.list():
            if artifact.manifest["scenario"]["scenarioId"] == scenario_id:
                return artifact
        fail("SCENARIO_NOT_FOUND", "scenarioId", "The requested study scenario is not installed.", details={"scenarioId": scenario_id})

    @staticmethod
    def _scenario_summary(artifact: SolutionArtifact) -> dict[str, Any]:
        manifest = artifact.manifest
        scenario = manifest["scenario"]
        return {
            "scenarioId": scenario["scenarioId"],
            "title": scenario["title"],
            "solutionId": manifest["solutionId"],
            "solutionVersion": manifest["version"],
            "rootNodeId": scenario["rootNodeId"],
            "game": manifest["game"],
            "solver": manifest["solver"],
            "accuracy": manifest["accuracy"],
            "trainerEligible": manifest["trainerEligible"],
            "practiceAvailable": True,
            "accuracyMode": "CERTIFIED" if manifest["trainerEligible"] else "REFERENCE_MODEL",
            "limitationCount": len(manifest["limitations"]),
            "nodeCount": len(manifest["nodes"]),
        }

    def _node_summary(self, artifact: SolutionArtifact, node_id: str) -> dict[str, Any]:
        node = artifact.node(node_id)
        self.rule_validator.validate(artifact, node_id)
        return {
            "nodeId": node["nodeId"],
            "actor": node["actor"],
            "actionHistory": node["actionHistory"],
            "potBb": node["potBb"],
            "actorStackBehindBb": node["actorStackBehindBb"],
            "amountToCallBb": node["amountToCallBb"],
            "actions": node["actions"],
            "childNodeByAction": node["childNodeByAction"],
        }
