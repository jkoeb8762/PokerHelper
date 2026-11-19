from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sqlite3
import statistics
import tempfile
import time
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from pokerhelper.api import create_app
from pokerhelper.application.catalog import bundled_solution_root
from pokerhelper.application.training import summarize_decisions


LOCAL_CACHE_ROOT = Path(__file__).resolve().parents[2] / ".cache"
LOCAL_CACHE_ROOT.mkdir(parents=True, exist_ok=True)


class ZeroRandom:
    def randbelow(self, upper: int) -> int:
        return 0


class Identifiers:
    def __init__(self) -> None:
        self.value = 0

    def __call__(self, prefix: str) -> str:
        self.value += 1
        return f"{prefix}:test-{self.value:04d}"


def _clock() -> str:
    return "2026-11-18T20:00:00.000Z"


def _session_request(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "scenarioId": "sb-vs-bb-100bb-after-folds",
        "nodeIds": ["node-000"],
        "heroPositions": ["SB"],
        "targetDecisions": 2,
        "feedbackMode": "IMMEDIATE",
        "rngEnabled": True,
        "acknowledgeApproximate": True,
    }
    result.update(overrides)
    return result


class TrainingApiTests(unittest.TestCase):
    def _app(self, directory: str):
        return create_app(
            data_dir=directory,
            seed_root=bundled_solution_root(),
            randomizer=ZeroRandom(),
            clock=_clock,
            id_factory=Identifiers(),
        )

    def test_reference_model_requires_explicit_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                response = client.post(
                    "/api/v1/training/sessions",
                    json=_session_request(acknowledgeApproximate=False),
                )
                self.assertEqual(422, response.status_code)
                self.assertEqual("TRAINER_APPROXIMATE_ACKNOWLEDGEMENT_REQUIRED", response.json()["error"]["code"])

    def test_immediate_flow_persists_exact_snapshot_and_rng(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                created = client.post("/api/v1/training/sessions", json=_session_request()).json()
                self.assertEqual("REFERENCE_MODEL", created["accuracyMode"])
                session_id = created["sessionId"]

                prompt = client.get(f"/api/v1/training/sessions/{session_id}/prompt").json()
                self.assertEqual(4, len(prompt["heroCombo"]))
                self.assertEqual("SB", prompt["heroPosition"])
                self.assertNotIn("referenceSnapshot", prompt)
                rng = client.post(f"/api/v1/training/sessions/{session_id}/prompt/rng").json()
                self.assertEqual(1, rng["roll"])
                self.assertEqual(1, rng["mapping"][0]["start"])
                self.assertEqual(100, rng["mapping"][-1]["end"])

                selected = prompt["offeredOptions"][0]["actionId"]
                result = client.post(
                    f"/api/v1/training/sessions/{session_id}/decisions",
                    json={"promptId": prompt["promptId"], "selectedOptionId": selected},
                ).json()
                self.assertTrue(result["feedbackVisible"])
                decision = result["decision"]
                evs = {item["optionId"]: Decimal(item["actionEvBb"]) for item in decision["referenceSnapshot"]}
                self.assertEqual(max(evs.values()) - evs[selected], Decimal(decision["evLossBb"]))
                self.assertEqual(prompt["heroCombo"], decision["heroCombo"])
                self.assertEqual(created["solutionId"], decision["solutionId"])
                self.assertEqual(1, decision["rngRoll"])

                second = client.get(f"/api/v1/training/sessions/{session_id}/prompt").json()
                complete = client.post(
                    f"/api/v1/training/sessions/{session_id}/decisions",
                    json={"promptId": second["promptId"], "selectedOptionId": second["offeredOptions"][0]["actionId"]},
                ).json()
                self.assertEqual("COMPLETED", complete["session"]["status"])
                review = client.get(f"/api/v1/training/sessions/{session_id}").json()
                self.assertEqual(2, review["summary"]["decisionsCompleted"])
                self.assertEqual(2, len(review["decisions"]))
                self.assertTrue(all(item["solutionVersion"] == created["solutionVersion"] for item in review["decisions"]))

    def test_delayed_feedback_remains_hidden_until_session_ends(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                created = client.post(
                    "/api/v1/training/sessions",
                    json=_session_request(feedbackMode="DELAYED", targetDecisions=3),
                ).json()
                session_id = created["sessionId"]
                prompt = client.get(f"/api/v1/training/sessions/{session_id}/prompt").json()
                submitted = client.post(
                    f"/api/v1/training/sessions/{session_id}/decisions",
                    json={"promptId": prompt["promptId"], "selectedOptionId": prompt["offeredOptions"][0]["actionId"]},
                ).json()
                self.assertFalse(submitted["feedbackVisible"])
                self.assertTrue(submitted["decision"]["feedbackPending"])
                self.assertEqual("0", submitted["session"]["summary"]["totalEvLossBb"])
                self.assertEqual([], submitted["session"]["summary"]["byGroupedHand"])
                decision_id = submitted["decision"]["decisionId"]
                self.assertEqual(
                    409,
                    client.get(f"/api/v1/training/sessions/{session_id}/decisions/{decision_id}").status_code,
                )
                hidden_detail = client.get(f"/api/v1/training/sessions/{session_id}").json()
                self.assertEqual("0", hidden_detail["summary"]["totalEvLossBb"])
                self.assertEqual(0, client.get("/api/v1/training/statistics").json()["decisionsCompleted"])
                client.post(f"/api/v1/training/sessions/{session_id}/complete")
                review = client.get(f"/api/v1/training/sessions/{session_id}").json()
                self.assertIn("referenceSnapshot", review["decisions"][0])
                self.assertEqual(1, client.get("/api/v1/training/statistics").json()["decisionsCompleted"])

    def test_invalid_action_does_not_create_a_decision(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                created = client.post("/api/v1/training/sessions", json=_session_request()).json()
                session_id = created["sessionId"]
                prompt = client.get(f"/api/v1/training/sessions/{session_id}/prompt").json()
                rejected = client.post(
                    f"/api/v1/training/sessions/{session_id}/decisions",
                    json={"promptId": prompt["promptId"], "selectedOptionId": "raise-to-999"},
                )
                self.assertEqual(422, rejected.status_code)
                self.assertEqual("TRAINER_OPTION_NOT_OFFERED", rejected.json()["error"]["code"])
                detail = client.get(f"/api/v1/training/sessions/{session_id}").json()
                self.assertEqual(0, detail["summary"]["decisionsCompleted"])

    def test_sessions_survive_restart_and_scenario_catalog_precedes_writes(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                created = client.post("/api/v1/training/sessions", json=_session_request()).json()
            connection = sqlite3.connect(f"{temporary}/pokerhelper.db")
            try:
                self.assertEqual("0001_phase3_training", connection.execute("select version_num from alembic_version").fetchone()[0])
                self.assertEqual(1, connection.execute("select count(*) from scenarios").fetchone()[0])
            finally:
                connection.close()
            with TestClient(self._app(temporary)) as client:
                sessions = client.get("/api/v1/training/sessions").json()["items"]
                self.assertEqual(created["sessionId"], sessions[0]["sessionId"])
                self.assertEqual(created["solutionId"], sessions[0]["solutionId"])

    def test_redrill_repeat_and_transactional_delete(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                created = client.post(
                    "/api/v1/training/sessions", json=_session_request(targetDecisions=1)
                ).json()
                source_id = created["sessionId"]
                prompt = client.get(f"/api/v1/training/sessions/{source_id}/prompt").json()
                client.post(
                    f"/api/v1/training/sessions/{source_id}/decisions",
                    json={"promptId": prompt["promptId"], "selectedOptionId": prompt["offeredOptions"][0]["actionId"]},
                )
                redrill = client.post(
                    f"/api/v1/training/sessions/{source_id}/redrill", json={"mode": "MISTAKES"}
                ).json()
                self.assertEqual("MISTAKE_REVIEW", redrill["drillType"])
                redrill_prompt = client.get(f"/api/v1/training/sessions/{redrill['sessionId']}/prompt").json()
                self.assertEqual(prompt["heroCombo"], redrill_prompt["heroCombo"])
                client.post(f"/api/v1/training/sessions/{redrill['sessionId']}/complete")
                repeated = client.post(f"/api/v1/training/sessions/{source_id}/repeat").json()
                self.assertEqual("REPEAT", repeated["drillType"])

                self.assertEqual(204, client.delete(f"/api/v1/training/sessions/{source_id}").status_code)
                self.assertEqual(404, client.get(f"/api/v1/training/sessions/{source_id}").status_code)
                detached = client.get(f"/api/v1/training/sessions/{redrill['sessionId']}").json()
                self.assertIsNone(detached["sourceSessionId"])

    def test_decision_rows_are_database_immutable(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            app = self._app(temporary)
            with TestClient(app) as client:
                created = client.post("/api/v1/training/sessions", json=_session_request(targetDecisions=1)).json()
                prompt = client.get(f"/api/v1/training/sessions/{created['sessionId']}/prompt").json()
                client.post(
                    f"/api/v1/training/sessions/{created['sessionId']}/decisions",
                    json={"promptId": prompt["promptId"], "selectedOptionId": prompt["offeredOptions"][0]["actionId"]},
                )
                with self.assertRaises(DatabaseError):
                    with app.state.database.engine.begin() as connection:
                        connection.execute(text("update training_decisions set ev_loss_bb = '999'"))

    def test_submit_feedback_p95_is_under_300_ms(self) -> None:
        with tempfile.TemporaryDirectory(dir=LOCAL_CACHE_ROOT) as temporary:
            with TestClient(self._app(temporary)) as client:
                created = client.post(
                    "/api/v1/training/sessions", json=_session_request(targetDecisions=20, rngEnabled=False)
                ).json()
                durations: list[float] = []
                for _ in range(20):
                    prompt = client.get(f"/api/v1/training/sessions/{created['sessionId']}/prompt").json()
                    started = time.perf_counter()
                    response = client.post(
                        f"/api/v1/training/sessions/{created['sessionId']}/decisions",
                        json={"promptId": prompt["promptId"], "selectedOptionId": prompt["offeredOptions"][0]["actionId"]},
                    )
                    durations.append((time.perf_counter() - started) * 1000)
                    self.assertEqual(200, response.status_code)
                p95 = statistics.quantiles(durations, n=20)[18]
                self.assertLess(p95, 300, f"Trainer submit p95 was {p95:.2f} ms")


class TrainingStatisticsTests(unittest.TestCase):
    def test_frequency_calibration_requires_50_comparable_decisions(self) -> None:
        decisions = []
        for index in range(50):
            decisions.append({
                "scenarioId": "scenario",
                "solutionId": "solution",
                "nodeId": "node-000",
                "groupedHand": "AKs",
                "heroPosition": "SB",
                "actionHistoryKey": "SB opening decision",
                "selectedOptionId": "call" if index < 30 else "raise",
                "evLossBb": "0.01",
                "feedbackSeverity": "NO_MATERIAL_EV_LOSS",
                "referenceSnapshot": [
                    {"optionId": "call", "frequency": "0.5", "actionEvBb": "0.1"},
                    {"optionId": "raise", "frequency": "0.5", "actionEvBb": "0.1"},
                ],
            })
        below = summarize_decisions(decisions[:49])
        self.assertEqual([], below["frequencyCalibration"]["buckets"])
        summary = summarize_decisions(decisions)
        bucket = summary["frequencyCalibration"]["buckets"][0]
        self.assertEqual(50, bucket["sampleSize"])
        call = bucket["actions"][0]
        self.assertEqual("0.6", call["observedFrequency"])
        self.assertEqual("10", call["deviationPp"])
        self.assertEqual("0.5", summary["totalEvLossBb"])


if __name__ == "__main__":
    unittest.main()
