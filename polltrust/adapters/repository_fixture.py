from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import PollSourceAdapter


class RepositoryFixtureAdapter(PollSourceAdapter):
    """Local deterministic adapter used for tests and manual normalized imports."""

    def __init__(self, path: str | Path, name: str = "repository-fixture"):
        self.path = Path(path)
        self.name = name

    def fetch(self) -> list[dict[str, Any]]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return payload["polls"] if isinstance(payload, dict) else payload
