#!/usr/bin/env python3
"""Audit PollTrust historical data and generated model.

This validator is intentionally deterministic. It validates internal invariants
and, when cached source HTML is available, reparses every configured source and
verifies that every persisted poll vector is reproduced from the source snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_historical_dataset import SOURCES, parse_wikipedia_archive, resolve_pollster


def _identity(poll: dict[str, Any]) -> tuple[Any, ...]:
    return (
        poll["pollster"],
        poll["election"],
        poll["date"],
        tuple(sorted((k, float(v)) for k, v in poll["parties"].items())),
    )


def _cache_path(url: str, cache_dir: Path) -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    return cache_dir / f"{key}.html"


def validate_dataset(raw: dict[str, Any], cache_dir: Path | None = None) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    elections = {e["id"]: e for e in raw.get("elections", [])}
    historical_pollsters = set(raw.get("historical_pollsters", []))
    polls = raw.get("polls", [])

    by_election = Counter()
    by_pollster = Counter()
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    aliases: dict[str, Counter[str]] = defaultdict(Counter)
    earliest: dict[str, str] = {}
    latest: dict[str, str] = {}
    exact_seen: set[tuple[Any, ...]] = set()
    duplicate_rows: list[dict[str, Any]] = []
    same_day: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    suspicious: list[dict[str, Any]] = []

    for election_id, election in elections.items():
        total = sum(float(v) for v in election.get("result", {}).values())
        if abs(total - 120.0) > 0.001:
            errors.append(f"official result {election_id} sums to {total}, not 120")
        try:
            date.fromisoformat(election["date"])
        except Exception:
            errors.append(f"invalid election date for {election_id}: {election.get('date')!r}")

    for idx, poll in enumerate(polls):
        required = {"pollster", "election", "date", "source", "parties"}
        missing = required - set(poll)
        if missing:
            errors.append(f"poll #{idx} missing fields {sorted(missing)}")
            continue
        if poll["pollster"] not in historical_pollsters:
            errors.append(f"poll #{idx} uses unknown historical pollster {poll['pollster']}")
        election = elections.get(poll["election"])
        if election is None:
            errors.append(f"poll #{idx} uses unknown election {poll['election']}")
            continue
        try:
            poll_day = date.fromisoformat(poll["date"])
        except ValueError:
            errors.append(f"poll #{idx} has invalid date {poll['date']!r}")
            continue
        election_day = date.fromisoformat(election["date"])
        if poll_day >= election_day:
            errors.append(f"leaking/future poll #{idx}: {poll['pollster']} {poll['date']} for {poll['election']}")
        if not isinstance(poll["source"], str) or not poll["source"].startswith(("http://", "https://")):
            errors.append(f"poll #{idx} has invalid source URL")
        seats = poll.get("parties")
        if not isinstance(seats, dict) or not seats:
            errors.append(f"poll #{idx} has empty party vector")
            continue
        total = 0.0
        for party, value in seats.items():
            if not isinstance(party, str) or not party:
                errors.append(f"poll #{idx} has invalid party identifier")
                continue
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"poll #{idx} has invalid seats for {party}: {value!r}")
                continue
            total += float(value)
            if float(value) > 50:
                suspicious.append({
                    "reason": "party_over_50_seats", "pollster": poll["pollster"],
                    "election": poll["election"], "date": poll["date"],
                    "party": party, "seats": value, "source": poll["source"],
                })
            if float(value) != int(float(value)):
                suspicious.append({
                    "reason": "fractional_mandate_projection", "pollster": poll["pollster"],
                    "election": poll["election"], "date": poll["date"],
                    "party": party, "seats": value, "source": poll["source"],
                })
        if abs(total - 120.0) > 0.001:
            errors.append(f"poll #{idx} sums to {total}, not 120")

        identity = _identity(poll)
        if identity in exact_seen:
            duplicate_rows.append({
                "pollster": poll["pollster"], "election": poll["election"],
                "date": poll["date"], "source": poll["source"],
            })
        exact_seen.add(identity)
        same_day[(poll["pollster"], poll["election"], poll["date"])].append(poll)

        by_election[poll["election"]] += 1
        by_pollster[poll["pollster"]] += 1
        matrix[poll["election"]][poll["pollster"]] += 1
        alias = str(poll.get("source_pollster_name", "")).strip()
        if alias:
            aliases[poll["pollster"]][alias] += 1
            resolved = resolve_pollster(alias)
            if resolved != poll["pollster"]:
                errors.append(
                    f"stored alias {alias!r} resolves to {resolved!r}, expected {poll['pollster']!r}"
                )
        old = earliest.get(poll["pollster"])
        earliest[poll["pollster"]] = min(old, poll["date"]) if old else poll["date"]
        old = latest.get(poll["pollster"])
        latest[poll["pollster"]] = max(old, poll["date"]) if old else poll["date"]

    same_day_competing = []
    for (pollster, election, poll_date), rows in same_day.items():
        vectors = {_identity(row)[3] for row in rows}
        if len(vectors) > 1:
            same_day_competing.append({
                "pollster": pollster, "election": election, "date": poll_date,
                "count": len(rows),
                "outlets": sorted({str(r.get("outlet") or "") for r in rows}),
                "sources": sorted({str(r.get("source")) for r in rows}),
            })

    source_reparse = {"performed": False, "missing_from_source_reparse": [], "source_counts": {}}
    if cache_dir is not None:
        all_cache_present = all(_cache_path(src["url"], cache_dir).exists() for src in SOURCES)
        if all_cache_present:
            source_reparse["performed"] = True
            reparsed: set[tuple[Any, ...]] = set()
            for src in SOURCES:
                html = _cache_path(src["url"], cache_dir).read_text(encoding="utf-8")
                rows = parse_wikipedia_archive(html, src["election"], src["url"])
                source_reparse["source_counts"][src["election"]] = len(rows)
                reparsed.update(_identity(row) for row in rows)
            for poll in polls:
                if _identity(poll) not in reparsed:
                    source_reparse["missing_from_source_reparse"].append({
                        "pollster": poll["pollster"], "election": poll["election"],
                        "date": poll["date"], "source": poll["source"],
                    })
            if source_reparse["missing_from_source_reparse"]:
                errors.append(
                    f"{len(source_reparse['missing_from_source_reparse'])} persisted polls were not reproduced from cached source snapshots"
                )

    provenance_diag = raw.get("provenance", {}).get("diagnostics", {})
    report = {
        "schema_version": 1,
        "valid": not errors,
        "poll_count": len(polls),
        "election_count": len(elections),
        "poll_counts_by_election": dict(sorted(by_election.items())),
        "poll_counts_by_pollster": dict(sorted(by_pollster.items())),
        "poll_counts_matrix": {
            election: dict(sorted(counts.items()))
            for election, counts in sorted(matrix.items())
        },
        "lineage_coverage": {
            pollster: {
                "earliest": earliest.get(pollster),
                "latest": latest.get(pollster),
                "elections": sorted({
                    p["election"] for p in polls if p["pollster"] == pollster
                }),
                "source_aliases": dict(aliases[pollster].most_common()),
            }
            for pollster in sorted(historical_pollsters)
        },
        "exact_duplicates_in_persisted_dataset": duplicate_rows,
        "same_day_competing_projections": same_day_competing,
        "suspicious_imported_values": suspicious,
        "source_reparse_verification": source_reparse,
        "parser_diagnostics": {
            "unmatched_pollster_names": provenance_diag.get("unmatched_pollster_names", {}),
            "unmatched_party_names": provenance_diag.get("unmatched_party_names", {}),
            "malformed_rows": provenance_diag.get("malformed_rows", []),
            "skipped_rows": provenance_diag.get("skipped_rows", []),
            "duplicates_removed": provenance_diag.get("duplicates_removed", []),
            "conflicting_same_day_rows": provenance_diag.get("conflicting_same_day_rows", []),
        },
        "errors": errors,
    }
    return report, errors


def validate_model(raw: dict[str, Any], model: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    active = {p["id"] for p in raw.get("active_pollsters", [])}
    model_pollsters = set(model.get("pollsters", {}))
    if active != model_pollsters:
        errors.append(f"model pollsters differ from active set: active={sorted(active)} model={sorted(model_pollsters)}")
    if model.get("demo_mode") is not False:
        errors.append("production historical model is still marked demo_mode")
    max_days = int(raw.get("analysis", {}).get("max_days_before", 120))
    expected_keys = {str(i) for i in range(max_days + 1)}
    for pollster_id, summary in model.get("pollsters", {}).items():
        curve = summary.get("expected_error_by_days", {})
        if set(curve) != expected_keys:
            errors.append(f"{pollster_id} reliability curve does not contain exactly 0..{max_days}")
        if summary.get("data_status") != "production":
            errors.append(f"{pollster_id} model data_status is not production")

    shared = raw.get("shared_prior", {})
    hist_id = shared.get("historical_id")
    if hist_id:
        completed = len({
            p["election"] for p in raw.get("polls", []) if p["pollster"] == hist_id
        })
        expected_support = round(float(shared.get("discount", 0.5)) * completed, 3)
        for target in shared.get("targets", []):
            actual = model.get("pollsters", {}).get(target, {}).get("shared_prior_effective_elections")
            if actual != expected_support:
                errors.append(
                    f"{target} shared prior support {actual!r} != expected {expected_support!r}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/historical-polls.json")
    parser.add_argument("--model", default=None)
    parser.add_argument("--cache-dir", default=".cache/historical")
    parser.add_argument("--output", default="data/historical-validation.json")
    args = parser.parse_args()

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    report, errors = validate_dataset(raw, cache_dir)
    if args.model:
        model = json.loads(Path(args.model).read_text(encoding="utf-8"))
        model_errors = validate_model(raw, model)
        report["model_errors"] = model_errors
        errors.extend(model_errors)
        report["valid"] = not errors
        report["errors"] = errors

    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "valid": report["valid"],
        "poll_count": report["poll_count"],
        "poll_counts_by_election": report["poll_counts_by_election"],
        "poll_counts_by_pollster": report["poll_counts_by_pollster"],
        "same_day_competing": len(report["same_day_competing_projections"]),
        "suspicious_values": len(report["suspicious_imported_values"]),
        "source_reparse_performed": report["source_reparse_verification"]["performed"],
        "source_reparse_missing": len(report["source_reparse_verification"]["missing_from_source_reparse"]),
        "errors": errors,
    }, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
