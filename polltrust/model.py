from __future__ import annotations

import random
from datetime import date, timedelta
from statistics import mean
from typing import Any

from .metrics import balanced_benchmark, bloc_total, directional_error, leave_one_election_out_debiased_errors, max_party_error, party_mae, party_rmse, seat_transfer_distance, summarize_errors


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _average_same_day(polls: list[dict[str, Any]]) -> dict[str, Any]:
    if len(polls) == 1:
        return polls[0]
    parties = sorted(set().union(*(set(p["parties"]) for p in polls)))
    averaged = {party: mean(float(p["parties"].get(party, 0)) for p in polls) for party in parties}
    return {**polls[0], "parties": averaged, "_same_day_aggregate_count": len(polls)}


def select_poll_at_horizon(polls: list[dict[str, Any]], election_date: date, days_before: int, max_staleness_days: int | None = 45) -> dict[str, Any] | None:
    cutoff = election_date - timedelta(days=days_before)
    eligible = [p for p in polls if parse_date(p["date"]) <= cutoff]
    if not eligible:
        return None
    chosen_date = max(parse_date(p["date"]) for p in eligible)
    if max_staleness_days is not None and (cutoff - chosen_date).days > max_staleness_days:
        return None
    return _average_same_day([p for p in eligible if parse_date(p["date"]) == chosen_date])


def _bootstrap_ci(values: list[float], seed: int = 26026, iterations: int = 2000) -> list[float] | None:
    if not values:
        return None
    if len(values) == 1:
        return [values[0], values[0]]
    rng = random.Random(seed)
    estimates = sorted(mean([rng.choice(values) for _ in values]) for _ in range(iterations))
    return [round(estimates[int(.025 * (len(estimates) - 1))], 4), round(estimates[int(.975 * (len(estimates) - 1))], 4)]


def _mean(values):
    return mean(values) if values else None


def _round(value):
    return None if value is None else round(value, 4)


def _election_bloc(raw: dict[str, Any], election: dict[str, Any]) -> list[str] | None:
    if "truth_bias_parties" in election:
        return election["truth_bias_parties"]
    return raw.get("analysis", {}).get("truth_bias_bloc_parties")



def _actual_for_selected_poll(selected: dict[str, Any], election: dict[str, Any]) -> dict[str, float]:
    actual = {k: float(v) for k, v in election["result"].items()}
    for group in selected.get("comparison_groups", []):
        key = group["key"]
        components = list(group.get("actual_components", []))
        actual[key] = sum(float(actual.pop(component, 0)) for component in components)
    return actual


def _records(raw, pollster_id, days_before, staleness):
    out = []
    for election in raw["elections"]:
        polls = [p for p in raw["polls"] if p["pollster"] == pollster_id and p["election"] == election["id"]]
        selected = select_poll_at_horizon(polls, parse_date(election["date"]), days_before, staleness)
        if selected:
            pred = selected["parties"]
            actual = _actual_for_selected_poll(selected, election)
            bloc = _election_bloc(raw, election)
            comparison_groups = selected.get("comparison_groups", [])
            out.append({
                "election_id": election["id"], "predicted": pred, "actual": actual,
                "error": seat_transfer_distance(pred, actual), "party_mae": party_mae(pred, actual),
                "party_rmse": party_rmse(pred, actual), "max_party_error": max_party_error(pred, actual),
                "directional_error": directional_error(pred, actual, bloc) if bloc and not comparison_groups else None,
                "truth_bias_parties": bloc,
                "same_day_aggregate_count": selected.get("_same_day_aggregate_count", 1),
            })
    return out


def _balanced_context(raw, days_before, staleness):
    result = {}
    for election in raw["elections"]:
        preds = []
        for pid in raw["historical_pollsters"]:
            polls = [p for p in raw["polls"] if p["pollster"] == pid and p["election"] == election["id"]]
            selected = select_poll_at_horizon(polls, parse_date(election["date"]), days_before, staleness)
            if selected:
                preds.append((pid, selected["parties"]))
        bench = balanced_benchmark(preds, raw["analysis"]["clusters"])
        bloc = _election_bloc(raw, election)
        result[election["id"]] = {
            "benchmark_bloc": bloc_total(bench, bloc) if bench and bloc else None,
            "actual_bloc": bloc_total(election["result"], bloc) if bloc else None,
        }
    return result


def _summary(raw, pid, staleness):
    rows = _records(raw, pid, 0, staleness)
    errors = [r["error"] for r in rows]
    stats = summarize_errors(errors)
    deb = leave_one_election_out_debiased_errors(rows)
    raw_mean, deb_mean = _mean(errors), _mean(deb)
    context = _balanced_context(raw, 0, staleness)
    leans, lvas, aligns, xs, ys = [], [], [], [], []

    for row in rows:
        c = context[row["election_id"]]
        bloc = row["truth_bias_parties"]
        if c["benchmark_bloc"] is None or not bloc:
            continue
        pred, bench, actual = bloc_total(row["predicted"], bloc), c["benchmark_bloc"], c["actual_bloc"]
        lean, truth = pred - bench, actual - bench
        leans.append(lean)
        lvas.append(abs(bench - actual) - abs(pred - actual))
        xs.append(truth)
        ys.append(lean)
        if lean and truth:
            aligns.append(1.0 if (lean > 0) == (truth > 0) else 0.0)

    alpha = beta = None
    if len(xs) >= 2:
        xb, yb = mean(xs), mean(ys)
        den = sum((x - xb) ** 2 for x in xs)
        if den:
            beta = sum((x - xb) * (y - yb) for x, y in zip(xs, ys)) / den
            alpha = yb - beta * xb

    directional = [r["directional_error"] for r in rows if r["directional_error"] is not None]
    return {
        "overall_raw_error": _round(raw_mean),
        "median_error": _round(stats["median"]),
        "consistency_stddev": _round(stats["stddev"]),
        "best_election_error": _round(stats["best"]),
        "worst_election_error": _round(stats["worst"]),
        "truth_bias": _round(_mean(directional)),
        "truth_bias_election_count": len(directional),
        "debiased_error": _round(deb_mean),
        "bias_cost": _round(raw_mean - deb_mean if raw_mean is not None and deb_mean is not None else None),
        "relative_lean": _round(_mean(leans)),
        "lean_value_added": _round(_mean(lvas)),
        "alignment_rate": _round(_mean(aligns)),
        "truth_responsiveness": {"alpha": _round(alpha), "beta": _round(beta)},
        "uncertainty_95": _bootstrap_ci(errors),
        "election_count": len(rows),
        "same_day_aggregate_elections": sum(1 for r in rows if r["same_day_aggregate_count"] > 1),
    }


def _curve(raw, pid, staleness, max_days):
    return {str(d): _round(_mean([r["error"] for r in _records(raw, pid, d, staleness)])) for d in range(max_days + 1)}


def _merge_prior(shared, independent, discount):
    ni = independent.get("election_count", 0) or 0
    ns = shared.get("election_count", 0) or 0
    prior = discount * ns
    merged = dict(independent)
    for key in ["overall_raw_error", "median_error", "consistency_stddev", "truth_bias", "debiased_error", "bias_cost", "relative_lean", "lean_value_added", "alignment_rate"]:
        a, b = independent.get(key), shared.get(key)
        den = (ni if a is not None else 0) + (prior if b is not None else 0)
        if den:
            merged[key] = _round(((a or 0) * ni + (b or 0) * prior) / den)
    merged.update({"effective_support": round(ni + prior, 3), "shared_prior_effective_elections": round(prior, 3), "independent_election_count": ni})
    return merged


def build_model(raw: dict[str, Any]) -> dict[str, Any]:
    max_days = int(raw["analysis"].get("max_days_before", 120))
    staleness = raw["analysis"].get("max_staleness_days", 45)
    summaries = {}
    for pollster in raw["active_pollsters"]:
        pid = pollster["id"]
        historical = pollster.get("historical_id", pid)
        base = _summary(raw, historical, staleness)
        base["expected_error_by_days"] = _curve(raw, historical, staleness, max_days)
        base["final_poll_accuracy"] = base["overall_raw_error"]
        base["effective_support"] = float(base["election_count"])
        base["independent_election_count"] = base["election_count"]
        base["shared_prior_effective_elections"] = 0.0
        base["name_he"] = pollster["name_he"]
        base["outlet_he"] = pollster.get("outlet_he")
        base["lineage_note_he"] = pollster.get("lineage_note_he")
        base["data_status"] = "demo" if raw.get("demo_mode") else "production"
        summaries[pid] = base

    shared_cfg = raw.get("shared_prior", {})
    shared_id = shared_cfg.get("historical_id")
    if shared_id:
        shared = _summary(raw, shared_id, staleness)
        shared_curve = _curve(raw, shared_id, staleness, max_days)
        discount = float(shared_cfg.get("discount", .5))
        for target in shared_cfg.get("targets", []):
            independent = summaries[target]
            merged = _merge_prior(shared, independent, discount)
            ni = independent.get("election_count", 0)
            prior = discount * shared.get("election_count", 0)
            curve = {}
            for d in range(max_days + 1):
                a, b = independent["expected_error_by_days"].get(str(d)), shared_curve.get(str(d))
                den = (ni if a is not None else 0) + (prior if b is not None else 0)
                curve[str(d)] = _round(((a or 0) * ni + (b or 0) * prior) / den if den else None)
            merged["expected_error_by_days"] = curve
            merged["final_poll_accuracy"] = merged.get("overall_raw_error")
            merged["name_he"] = independent["name_he"]
            merged["outlet_he"] = independent["outlet_he"]
            merged["lineage_note_he"] = independent["lineage_note_he"]
            merged["data_status"] = independent["data_status"]
            summaries[target] = merged

    return {
        "schema_version": 2,
        "generated_at": raw["as_of"],
        "demo_mode": bool(raw.get("demo_mode")),
        "methodology": {
            "primary_metric": "SeatTransferDistance = 0.5 * sum(abs(predicted - actual))",
            "historical_unit": "election",
            "horizon_rule": "latest poll date available by election_date - X; pre-final-list party schemas are normalized to the eventual election lists/groups; same-day target-pollster polls are averaged; no future polls",
            "max_staleness_days": staleness,
            "shared_prior_discount": shared_cfg.get("discount"),
            "truth_bias_bloc": "election-specific party/list mapping; elections without a defensible mapping are excluded",
            "relative_lean_benchmark": "cluster-balanced benchmark",
            "debiased_precision": "leave-one-election-out correction only for party identifiers comparable across elections",
        },
        "pollsters": summaries,
    }
