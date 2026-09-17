import json
from datetime import date
from pathlib import Path

from polltrust.schemas import validate_poll
from scripts.validate_historical_dataset import validate_dataset, validate_model

ROOT = Path(__file__).resolve().parents[1]


def test_current_poll_file_is_valid():
    election = json.loads((ROOT / "data/election.json").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "data/current-polls.json").read_text(encoding="utf-8"))
    active = set(election["pollsters"])
    assert current["polls"], "current poll dataset must not be empty in production"
    assert {poll["pollster"] for poll in current["polls"]} == active
    for poll in current["polls"]:
        validate_poll(poll, active)
        assert date.fromisoformat(poll["date"]) < date.fromisoformat(election["election_date"])
    assert current.get("last_successful_check")


def test_committed_historical_dataset_is_production_and_valid():
    raw = json.loads((ROOT / "data/historical-polls.json").read_text(encoding="utf-8"))
    report, errors = validate_dataset(raw)
    assert raw["demo_mode"] is False
    assert report["poll_count"] > 0
    assert errors == []


def test_committed_historical_model_is_production_and_matches_active_pollsters():
    election = json.loads((ROOT / "data/election.json").read_text(encoding="utf-8"))
    raw = json.loads((ROOT / "data/historical-polls.json").read_text(encoding="utf-8"))
    model = json.loads((ROOT / "data/historical-model.json").read_text(encoding="utf-8"))
    assert model["demo_mode"] is False
    assert set(model["pollsters"]) == set(election["pollsters"])
    assert validate_model(raw, model) == []


def test_historical_polls_are_strictly_before_their_election():
    raw = json.loads((ROOT / "data/historical-polls.json").read_text(encoding="utf-8"))
    election_dates = {e["id"]: date.fromisoformat(e["date"]) for e in raw["elections"]}
    for poll in raw["polls"]:
        assert date.fromisoformat(poll["date"]) < election_dates[poll["election"]]
        assert abs(sum(float(v) for v in poll["parties"].values()) - 120) < 0.001


def test_new_entities_do_not_gain_invented_completed_election_history():
    model = json.loads((ROOT / "data/historical-model.json").read_text(encoding="utf-8"))
    assert model["pollsters"]["hamadad_consortium"]["election_count"] == 0
    assert model["pollsters"]["tatika"]["election_count"] == 0


def test_direct_polls_shared_prior_is_discounted_and_not_counted_as_independent():
    raw = json.loads((ROOT / "data/historical-polls.json").read_text(encoding="utf-8"))
    model = json.loads((ROOT / "data/historical-model.json").read_text(encoding="utf-8"))
    shared_elections = {
        p["election"] for p in raw["polls"] if p["pollster"] == "direct_polls_shared"
    }
    expected = len(shared_elections) * raw["shared_prior"]["discount"]
    for target in ("direct_polls_sharon", "next_data_filber"):
        summary = model["pollsters"][target]
        assert summary["independent_election_count"] == 0
        assert summary["shared_prior_effective_elections"] == expected
