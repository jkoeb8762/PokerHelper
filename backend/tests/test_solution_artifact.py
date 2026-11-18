from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from pokerhelper.application.catalog import bundled_solution_root
from pokerhelper.domain.errors import DomainError
from pokerhelper.solutions import SolutionArtifact, SolutionStore
from pokerhelper.solutions.artifact import solution_id_for_manifest


def bundled_artifact_path() -> Path:
    manifests = tuple(bundled_solution_root().glob("*/manifest.json"))
    if len(manifests) != 1:
        raise AssertionError(f"expected one bundled artifact, received {len(manifests)}")
    return manifests[0].parent


class SolutionArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = SolutionArtifact.load(bundled_artifact_path())

    def test_bundled_artifact_is_complete_and_provenanced(self) -> None:
        self.assertEqual(18, len(self.artifact.nodes))
        self.assertEqual(
            "6d54d3725c50d5e74c8971723a616eb52d664f3c",
            self.artifact.manifest["source"]["commit"],
        )
        self.assertEqual("MIT", self.artifact.manifest["authorization"]["license"])
        self.assertFalse(self.artifact.manifest["trainerEligible"])
        for node in self.artifact.nodes.values():
            self.assertEqual(169, len(node["groupedHands"]))
            self.assertEqual(1326, len(node["exactCombos"]))

    def test_exact_suits_survive_with_group_mapping(self) -> None:
        root = self.artifact.node("node-000")
        self.assertIn("AsKs", root["exactCombos"])
        self.assertIn("AhKh", root["exactCombos"])
        self.assertEqual("AKs", root["exactCombos"]["AsKs"]["group"])
        self.assertNotEqual("AsKs", "AhKh")

    def test_representative_values_match_pinned_source_snapshot(self) -> None:
        cases = {
            ("node-000", "AsKs", "raise-to-2.5"): ("0.682444608122", "1.999560523426"),
            ("node-000", "7s2d", "fold"): ("0.680189415006", "0"),
            ("node-028", "AsAh", "raise-to-7.5"): ("0.999795335938", "8.162042495218"),
            ("node-031", "AsAh", "raise-to-22.5"): ("0.998008911144", "22.050333175852"),
        }
        for (node_id, combo, action_id), (frequency, ev) in cases.items():
            strategy = self.artifact.node(node_id)["exactCombos"][combo]
            self.assertEqual(frequency, strategy["frequencies"][action_id])
            self.assertEqual(ev, strategy["evBb"][action_id])

    def test_rejects_non_normalized_frequencies(self) -> None:
        error = self._mutated_error(lambda node: node["exactCombos"]["AsAh"]["frequencies"].update({"fold": "0.9"}))
        self.assertEqual("SOLUTION_FREQUENCY_NOT_NORMALIZED", error.code)

    def test_rejects_missing_or_impossible_combo_set(self) -> None:
        def remove_combo(node: dict) -> None:
            node["exactCombos"].pop("AsAh")
            node["exactCombos"]["AsAs"] = {
                "group": "AA", "reachFrequency": "1",
                "frequencies": {action["actionId"]: "0" for action in node["actions"]},
                "evBb": {action["actionId"]: "0" for action in node["actions"]},
            }

        error = self._mutated_error(remove_combo)
        self.assertEqual("SOLUTION_COMBO_SET_INVALID", error.code)

    def test_rejects_unknown_action_type(self) -> None:
        error = self._mutated_error(lambda node: node["actions"][0].update({"type": "BET"}))
        self.assertEqual("SOLUTION_ACTION_TYPE_INVALID", error.code)

    def test_rejects_unreferenced_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            shutil.copytree(bundled_artifact_path(), target)
            (target / "untrusted.py").write_text("raise RuntimeError('never execute artifact content')\n", encoding="utf-8")
            with self.assertRaises(DomainError) as caught:
                SolutionArtifact.load(target)
        self.assertEqual("SOLUTION_FILE_SET_INVALID", caught.exception.code)

    def test_trainer_eligibility_requires_absolute_accuracy_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            shutil.copytree(bundled_artifact_path(), target)
            manifest_path = target / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["trainerEligible"] = True
            manifest["solutionId"] = solution_id_for_manifest(manifest)
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(DomainError) as caught:
                SolutionArtifact.load(target)
        self.assertEqual("SOLUTION_TRAINER_ACCURACY_INSUFFICIENT", caught.exception.code)

    def test_tampering_is_caught_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            shutil.copytree(bundled_artifact_path(), target)
            node_path = target / "nodes" / "node-000.json"
            node_path.write_bytes(node_path.read_bytes() + b" ")
            with self.assertRaises(DomainError) as caught:
                SolutionArtifact.load(target)
        self.assertEqual("SOLUTION_NODE_HASH_MISMATCH", caught.exception.code)

    def test_publication_is_idempotent_and_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = SolutionStore(Path(temporary) / "solutions")
            first = store.publish(bundled_artifact_path())
            second = store.publish(bundled_artifact_path())
            self.assertTrue(first.published)
            self.assertFalse(second.published)
            self.assertEqual(first.artifact.solution_id, second.artifact.solution_id)
            self.assertEqual(1, len(tuple((Path(temporary) / "solutions").glob("*/manifest.json"))))

    def _mutated_error(self, mutation) -> DomainError:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            shutil.copytree(bundled_artifact_path(), target)
            manifest_path = target / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            reference = manifest["nodes"][0]
            node_path = target / reference["path"]
            node = json.loads(node_path.read_text(encoding="utf-8"))
            mutation(node)
            raw = (json.dumps(node, indent=2, sort_keys=True) + "\n").encode("utf-8")
            node_path.write_bytes(raw)
            reference["sha256"] = hashlib.sha256(raw).hexdigest()
            manifest["solutionId"] = solution_id_for_manifest(manifest)
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(DomainError) as caught:
                SolutionArtifact.load(target)
            return caught.exception


if __name__ == "__main__":
    unittest.main()
