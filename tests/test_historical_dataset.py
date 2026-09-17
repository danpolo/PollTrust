from collections import Counter

from scripts.build_historical_dataset import (
    ELECTIONS,
    SOURCES,
    parse_wikipedia_archive,
    resolve_pollster,
)


def test_english_archive_parser_supports_older_midgam():
    html = """<table>
    <tr><th>Date</th><th>Polling firm</th><th>Publisher</th><th>Blue &amp; White</th><th>Likud</th><th>Joint List</th><th>Emet</th><th>Shas</th><th>Yisrael Beitenu</th><th>UTJ</th><th>Yamina</th><th>Otzma</th><th>Gov.</th></tr>
    <tr><td>28 Feb 2020</td><td>Midgam</td><td>Channel 12</td><td>33</td><td>36</td><td>15</td><td>7</td><td>9</td><td>7</td><td>7</td><td>6</td><td>0</td><td>58</td></tr>
    </table>"""
    rows = parse_wikipedia_archive(
        html,
        "knesset-23",
        "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2020_Israeli_legislative_election",
    )
    assert len(rows) == 1
    assert rows[0]["pollster"] == "midgam_geva"
    assert sum(rows[0]["parties"].values()) == 120


def test_alias_resolution_is_conservative():
    assert resolve_pollster("KANTAR") == "kantar_hasid"
    assert resolve_pollster("TNS/Kan") is None
    assert resolve_pollster("Teleseker/Channel 1") is None
    assert resolve_pollster("Panel Project HaMidgam") is None
    assert resolve_pollster("Knesset Channel/Panels Politics") == "lazar_research"
    assert resolve_pollster("Maariv/Ma'agar Mochot") == "maagar_mohot"
    assert resolve_pollster("Direct Polls") == "direct_polls_shared"


def test_non_120_target_row_is_reported_not_imported():
    html = """<table>
    <tr><th>Date</th><th>Polling firm</th><th>Publisher</th><th>Blue &amp; White</th><th>Likud</th><th>Joint List</th><th>Emet</th><th>Shas</th><th>Yisrael Beitenu</th><th>UTJ</th><th>Yamina</th><th>Otzma</th><th>Gov.</th></tr>
    <tr><td>28 Feb 2020</td><td>Midgam</td><td>Channel 12</td><td>33</td><td>36</td><td>15</td><td>7</td><td>9</td><td>7</td><td>7</td><td>5</td><td>0</td><td>58</td></tr>
    </table>"""
    diagnostics = {}
    rows = parse_wikipedia_archive(
        html,
        "knesset-23",
        "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2020_Israeli_legislative_election",
        diagnostics=diagnostics,
    )
    assert rows == []
    assert any(r["reason"] == "seat_total_not_120" for r in diagnostics["skipped_rows"])


def test_history_is_configured_back_through_2009():
    elections = {s["election"] for s in SOURCES}
    assert {
        "knesset-18", "knesset-19", "knesset-20", "knesset-21",
        "knesset-22", "knesset-23", "knesset-24", "knesset-25",
    } <= elections


def test_official_result_vectors_are_exactly_120():
    assert all(sum(e["result"].values()) == 120 for e in ELECTIONS.values())
