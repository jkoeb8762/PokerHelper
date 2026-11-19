"""Command-line launcher and solution maintenance commands."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from pokerhelper.solutions import SolutionArtifact, SolutionStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pokerhelper")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Run the local Study and Trainer application")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--data-dir", type=Path, default=Path("data"))
    serve.add_argument("--reload", action="store_true")

    validate = commands.add_parser("validate-solution", help="Validate an immutable solution directory")
    validate.add_argument("path", type=Path)

    publish = commands.add_parser("import-solution", help="Validate and publish a solution into local data")
    publish.add_argument("path", type=Path)
    publish.add_argument("--data-dir", type=Path, default=Path("data"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "validate-solution":
        artifact = SolutionArtifact.load(args.path)
        print(f"valid {artifact.solution_id} ({len(artifact.nodes)} nodes)")
        return
    if args.command == "import-solution":
        result = SolutionStore(args.data_dir.resolve() / "solutions").publish(args.path)
        verb = "published" if result.published else "already installed"
        print(f"{verb}: {result.artifact.solution_id}")
        return
    if args.reload:
        os.environ["POKERHELPER_DATA_DIR"] = str(args.data_dir.resolve())
        uvicorn.run("pokerhelper.api:app", host="127.0.0.1", port=args.port, reload=True)
        return
    from pokerhelper.api import create_app

    application = create_app(data_dir=args.data_dir)
    uvicorn.run(application, host="127.0.0.1", port=args.port)
