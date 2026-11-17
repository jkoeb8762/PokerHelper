from __future__ import annotations

from pathlib import Path
import json
import sys
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BACKEND_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def load_json(name: str) -> Any:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as fixture:
        return json.load(fixture)

