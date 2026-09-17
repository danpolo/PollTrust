from __future__ import annotations

from collections.abc import Iterable, Mapping
from math import sqrt
from statistics import mean, median, pstdev


def _party_keys(predicted: Mapping[str, float], actual: Mapping[str, float]) -> set[str]:
    return set(predicted) | set(actual)


def seat_transfer_distance(predicted: Mapping[str, float], actual: Mapping[str, float]) -> float:
    return 0.5 * sum(abs(float(predicted.get(k, 0)) - float(actual.get(k, 0))) for k in _party_keys(predicted, actual))


def party_mae(predicted: Mapping[str, float], actual: Mapping[str, float]) -> float:
    keys = _party_keys(predicted, actual)
    return mean(abs(float(predicted.get(k, 0)) - float(actual.get(k, 0))) for k in keys) if keys else 0.0


def party_rmse(predicted: Mapping[str, float], actual: Mapping[str, float]) -> float:
    keys = _party_keys(predicted, actual)
    return sqrt(mean((float(predicted.get(k, 0)) - float(actual.get(k, 0))) ** 2 for k in keys)) if keys else 0.0


def max_party_error(predicted: Mapping[str, float], actual: Mapping[str, float]) -> float:
    keys = _party_keys(predicted, actual)
    return max((abs(float(predicted.get(k, 0)) - float(actual.get(k, 0))) for k in keys), default=0.0)


def bloc_total(seats: Mapping[str, float], bloc_parties: Iterable[str]) -> float:
    return sum(float(seats.get(p, 0)) for p in bloc_parties)


def bloc_absolute_error(predicted: Mapping[str, float], actual: Mapping[str, float], bloc_parties: Iterable[str]) -> float:
    return abs(bloc_total(predicted, bloc_parties) - bloc_total(actual, bloc_parties))


def directional_error(predicted: Mapping[str, float], actual: Mapping[str, float], bloc_parties: Iterable[str]) -> float:
    return bloc_total(predicted, bloc_parties) - bloc_total(actual, bloc_parties)


def summarize_errors(errors: list[float]) -> dict[str, float | None]:
    if not errors:
        return {"mean": None, "median": None, "stddev": None, "best": None, "worst": None}
    return {"mean": mean(errors), "median": median(errors), "stddev": pstdev(errors) if len(errors) > 1 else 0.0, "best": min(errors), "worst": max(errors)}


def balanced_benchmark(predictions: list[tuple[str, Mapping[str, float]]], clusters: Mapping[str, str]) -> dict[str, float]:
    if not predictions:
        return {}
    by_cluster: dict[str, list[Mapping[str, float]]] = {}
    for pollster_id, seats in predictions:
        by_cluster.setdefault(clusters.get(pollster_id, pollster_id), []).append(seats)
    all_parties = set().union(*(set(s) for _, s in predictions))
    centers = [{p: mean(float(r.get(p, 0)) for r in rows) for p in all_parties} for rows in by_cluster.values()]
    return {p: mean(center[p] for center in centers) for p in all_parties}


def leave_one_election_out_debiased_errors(records: list[dict]) -> list[float]:
    """Correct only party identifiers that are comparable across elections.

    A party/list that exists only in the held-out election receives no invented
    correction. Likewise, parties that existed only in other elections are not
    injected into the held-out vector. This matters in Israel where alliances
    and candidate lists change frequently between election cycles.
    """
    output: list[float] = []
    for i, row in enumerate(records):
        others = [r for j, r in enumerate(records) if j != i]
        if not others:
            output.append(seat_transfer_distance(row["predicted"], row["actual"]))
            continue
        target_parties = set(row["predicted"]) | set(row["actual"])
        corrected: dict[str, float] = {}
        for party in target_parties:
            comparable = [
                float(r["predicted"].get(party, 0)) - float(r["actual"].get(party, 0))
                for r in others
                if party in r["predicted"] or party in r["actual"]
            ]
            correction = mean(comparable) if comparable else 0.0
            corrected[party] = float(row["predicted"].get(party, 0)) - correction
        output.append(seat_transfer_distance(corrected, row["actual"]))
    return output
