"""Atomic publication and cached reads for immutable solution artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import tempfile
import threading
from typing import Any

from pokerhelper.domain.errors import fail

from .artifact import SolutionArtifact


@dataclass(frozen=True, slots=True)
class PublishResult:
    artifact: SolutionArtifact
    published: bool


class SolutionStore:
    """Filesystem content store; published solution IDs are never mutated."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, SolutionArtifact] = {}
        self._lock = threading.RLock()

    @staticmethod
    def directory_name(solution_id: str) -> str:
        return solution_id.rsplit(":", 1)[-1]

    def publish(self, source: str | Path) -> PublishResult:
        candidate = SolutionArtifact.load(source)
        target = self.root / self.directory_name(candidate.solution_id)
        with self._lock:
            if target.exists():
                existing = SolutionArtifact.load(target)
                if existing.manifest != candidate.manifest:
                    fail(
                        "SOLUTION_VERSION_CONFLICT",
                        "manifest.solutionId",
                        "A different artifact already occupies this immutable solution ID.",
                        details={"solutionId": candidate.solution_id},
                    )
                self._cache[candidate.solution_id] = existing
                return PublishResult(existing, False)

            staging_parent = self.root / ".staging"
            staging_parent.mkdir(exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix="solution-", dir=staging_parent))
            try:
                copied = staging / "artifact"
                shutil.copytree(candidate.path, copied)
                SolutionArtifact.load(copied)
                copied.replace(target)
                published = SolutionArtifact.load(target)
                self._cache[published.solution_id] = published
                return PublishResult(published, True)
            finally:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)

    def get(self, solution_id: str) -> SolutionArtifact:
        with self._lock:
            cached = self._cache.get(solution_id)
            if cached is not None:
                return cached
            target = self.root / self.directory_name(solution_id)
            if not target.exists():
                fail("SOLUTION_NOT_FOUND", "solutionId", "The requested solution is not installed.", details={"solutionId": solution_id})
            artifact = SolutionArtifact.load(target)
            if artifact.solution_id != solution_id:
                fail("SOLUTION_STORE_ID_MISMATCH", "solutionId", "The installed directory contains a different solution ID.")
            self._cache[solution_id] = artifact
            return artifact

    def list(self) -> tuple[SolutionArtifact, ...]:
        artifacts: list[SolutionArtifact] = []
        with self._lock:
            for manifest_path in sorted(self.root.glob("*/manifest.json")):
                artifact = SolutionArtifact.load(manifest_path.parent)
                self._cache[artifact.solution_id] = artifact
                artifacts.append(artifact)
        return tuple(artifacts)

    def write_index(self) -> Path:
        """Write a deterministic diagnostic index; artifacts remain authoritative."""

        entries = [
            {
                "solutionId": artifact.solution_id,
                "version": artifact.manifest["version"],
                "title": artifact.manifest["title"],
                "scenarioId": artifact.scenario["scenarioId"],
            }
            for artifact in self.list()
        ]
        path = self.root / "index.json"
        path.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
