from datetime import date

from polltrust.demo_data import build_demo_raw
from polltrust.model import build_model, select_poll_at_horizon


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
