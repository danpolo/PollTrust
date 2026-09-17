from __future__ import annotations

from datetime import date
from typing import Any


class ValidationError(ValueError):
    pass


def validate_poll(poll: dict[str, Any], active_pollsters: set[str] | None = None) -> None:
    required = {"pollster", "date", "source", "parties"}
    missing = required - poll.keys()
    if missing:
        raise ValidationError(f"poll missing fields: {sorted(missing)}")
    if active_pollsters is not None and poll["pollster"] not in active_pollsters:
        raise ValidationError(f"unknown pollster: {poll['pollster']}")
    try:
        date.fromisoformat(str(poll["date"]))
    except ValueError as exc:
        raise ValidationError(f"invalid date: {poll['date']}") from exc
    if not isinstance(poll["source"], str) or not poll["source"].startswith(("http://", "https://")):
        raise ValidationError("source must be an http(s) URL")
    if not isinstance(poll["parties"], dict) or not poll["parties"]:
        raise ValidationError("parties must be a non-empty object")
    total = 0.0
    for party, seats in poll["parties"].items():
        if not isinstance(party, str) or not party:
            raise ValidationError("party identifiers must be non-empty strings")
        if not isinstance(seats, (int, float)) or seats < 0:
            raise ValidationError(f"invalid seats for {party}: {seats}")
        total += float(seats)
    if abs(total - 120) > 0.001:
        raise ValidationError(f"seat total must equal 120, got {total}")


def poll_identity(poll: dict[str, Any]) -> tuple[str, str, tuple[tuple[str, float], ...]]:
    return (str(poll["pollster"]), str(poll["date"]), tuple(sorted((str(k), float(v)) for k, v in poll["parties"].items())))
