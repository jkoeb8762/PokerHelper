from __future__ import annotations

from pathlib import Path
import statistics
import tempfile
import time
import unittest

from fastapi.testclient import TestClient

from pokerhelper.api import create_app
from pokerhelper.application.catalog import bundled_solution_root


class StudyApiTests(unittest.TestCase):
    def test_catalog_node_and_assumptions_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_dir=temporary, seed_root=bundled_solution_root())
            with TestClient(app) as client:
                health = client.get("/api/v1/health")
                self.assertEqual(200, health.status_code)
                self.assertEqual("local-offline", health.json()["mode"])

                scenarios = client.get("/api/v1/scenarios").json()["items"]
                self.assertEqual(1, len(scenarios))
                scenario = scenarios[0]
                self.assertEqual(18, scenario["nodeCount"])
                self.assertFalse(scenario["trainerEligible"])

                detail = client.get(f"/api/v1/scenarios/{scenario['scenarioId']}").json()
                self.assertEqual(18, len(detail["nodes"]))
                self.assertEqual("node-000", detail["rootNodeId"])

                solution_id = scenario["solutionId"]
                node = client.get(f"/api/v1/solutions/{solution_id}/nodes/node-000")
                self.assertEqual(200, node.status_code)
                payload = node.json()
                self.assertEqual(169, len(payload["groupedHands"]))
                self.assertEqual(1326, len(payload["exactCombos"]))
                self.assertIn("AsKs", payload["exactCombos"])

                assumptions = client.get(f"/api/v1/solutions/{solution_id}/assumptions").json()
                self.assertEqual("NO_RAKE_SOURCE_V1", assumptions["game"]["rake"]["policyVersion"])
                self.assertIsNone(assumptions["accuracy"]["modelAccuracyBoundBb"])

    def test_cached_common_node_p95_is_under_200_ms(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_dir=temporary, seed_root=bundled_solution_root())
            with TestClient(app) as client:
                scenario = client.get("/api/v1/scenarios").json()["items"][0]
                path = f"/api/v1/solutions/{scenario['solutionId']}/nodes/node-000"
                self.assertEqual(200, client.get(path).status_code)
                durations: list[float] = []
                for _ in range(20):
                    start = time.perf_counter()
                    response = client.get(path)
                    durations.append((time.perf_counter() - start) * 1000)
                    self.assertEqual(200, response.status_code)
                p95 = statistics.quantiles(durations, n=20)[18]
                self.assertLess(p95, 200, f"node endpoint p95 was {p95:.2f} ms")

    def test_missing_node_returns_structured_404(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_dir=temporary, seed_root=bundled_solution_root())
            with TestClient(app) as client:
                scenario = client.get("/api/v1/scenarios").json()["items"][0]
                response = client.get(f"/api/v1/solutions/{scenario['solutionId']}/nodes/node-999")
                self.assertEqual(404, response.status_code)
                self.assertEqual("SOLUTION_NODE_NOT_FOUND", response.json()["error"]["code"])

    def test_bookmarked_study_route_serves_spa_shell(self) -> None:
        frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
        if not frontend_dist.exists():
            self.skipTest("production frontend has not been built")
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(data_dir=temporary, seed_root=bundled_solution_root(), frontend_dist=frontend_dist)
            with TestClient(app) as client:
                response = client.get("/study/sb-vs-bb-100bb-after-folds/node-028?combo=AsKs")
                self.assertEqual(200, response.status_code)
                self.assertIn("PokerHelper · Study", response.text)


if __name__ == "__main__":
    unittest.main()
