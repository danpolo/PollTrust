from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from .schemas import poll_identity, validate_poll


def merge_polls(existing_doc: dict[str, Any], incoming: list[dict[str, Any]], active_pollsters: set[str]) -> tuple[dict[str, Any], int]:
    """Validate all incoming rows first; return unchanged data if validation raises."""
    for poll in incoming:
        validate_poll(poll, active_pollsters)
    output = copy.deepcopy(existing_doc)
    existing_ids = {poll_identity(p) for p in output.get("polls", [])}
    added = 0
    for poll in incoming:
        pid = poll_identity(poll)
        if pid not in existing_ids:
            output.setdefault("polls", []).append(poll)
            existing_ids.add(pid)
            added += 1
    if added:
        output["polls"].sort(key=lambda p: (p["date"], p["pollster"]), reverse=True)
        output["last_successful_update"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return output, added
