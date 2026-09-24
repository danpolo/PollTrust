import json
from pathlib import Path
from datetime import date

from polltrust.demo_data import build_demo_raw
from polltrust.model import _actual_for_selected_poll, build_model, select_poll_at_horizon


def test_horizon_never_uses_future_poll():
    polls = [
        {"date": "2026-09-01", "parties": {"a": 60, "b": 60}},
        {"date": "2026-09-20", "parties": {"a": 70, "b": 50}},
    ]
    assert select_poll_at_horizon(polls, date(2026, 10, 1), 20, 45)["date"] == "2026-09-01"


def test_stale_poll_can_be_excluded():
    assert select_poll_at_horizon(
        [{"date": "2026-01-01", "parties": {"a": 60, "b": 60}}],
        date(2026, 10, 1),
        20,
        45,
    ) is None


def test_same_day_polls_are_averaged_instead_of_arbitrarily_selected():
    chosen = select_poll_at_horizon(
        [
            {"date": "2026-09-10", "parties": {"a": 60, "b": 60}},
            {"date": "2026-09-10", "parties": {"a": 64, "b": 56}},
            {"date": "2026-09-01", "parties": {"a": 50, "b": 70}},
        ],
        date(2026, 10, 1),
        20,
        45,
    )
    assert chosen["parties"] == {"a": 62, "b": 58}
    assert chosen["_same_day_aggregate_count"] == 2


def test_shared_prior_is_discounted():
    model = build_model(build_demo_raw())["pollsters"]["direct_polls_sharon"]
    assert model["independent_election_count"] == 0
    assert model["shared_prior_effective_elections"] == 1.5



def test_grouped_early_poll_collapses_election_truth_the_same_way():
    selected = {
        "comparison_groups": [{
            "key": "joint_pre_split",
            "actual_components": ["hadash_taal", "balad"],
        }]
    }
    election = {"result": {"hadash_taal": 5, "balad": 0, "raam": 5, "likud": 110}}
    assert _actual_for_selected_poll(selected, election) == {
        "joint_pre_split": 5.0,
        "raam": 5.0,
        "likud": 110.0,
    }



def test_production_history_extends_beyond_final_list_cutoff():
    model = json.loads(Path("data/historical-model.json").read_text(encoding="utf-8"))
    expected_minimum_horizons = {
        "midgam_geva": 120,
        "kantar_hasid": 100,
        "lazar_research": 100,
        "maagar_mohot": 100,
        "direct_polls_sharon": 100,
        "next_data_filber": 100,
    }
    for pollster_id, minimum_day in expected_minimum_horizons.items():
        curve = model["pollsters"][pollster_id]["expected_error_by_days"]
        non_null_days = [int(day) for day, value in curve.items() if value is not None]
        assert max(non_null_days) >= minimum_day, pollster_id
