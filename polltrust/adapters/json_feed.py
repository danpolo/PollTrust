from __future__ import annotations

import json
from typing import Any
from urllib.request import Request, urlopen

from .base import PollSourceAdapter


class JsonFeedAdapter(PollSourceAdapter):
    """Deterministic adapter for a normalized remote JSON feed."""

    def __init__(self, name: str, url: str, timeout: int = 20):
        self.name = name
        self.url = url
        self.timeout = timeout

    def fetch(self) -> list[dict[str, Any]]:
        req = Request(self.url, headers={"User-Agent": "PollTrust/0.1 (+https://github.com/danpolo/PollTrust)"})
        with urlopen(req, timeout=self.timeout) as response:
            payload = json.load(response)
        if isinstance(payload, dict):
            payload = payload.get("polls", [])
        if not isinstance(payload, list):
            raise ValueError(f"{self.name}: JSON root must be a list or {{polls: []}}")
        return payload
