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


def test_year_section_prevents_old_rows_being_inferred_as_election_year():
    html = """<table>
    <tr><th>Date</th><th>Polling firm</th><th>Likud</th><th>Yisrael Beitenu</th><th>Yesh Atid</th><th>Zionist Union</th><th>Jewish Home</th><th>Shas</th><th>UTJ</th><th>Meretz</th><th>Joint List</th><th>Yachad</th><th>Kulanu</th></tr>
    <tr><td>3 Feb 2015</td><td>Panels/Knesset Channel</td><td>25</td><td>5</td><td>11</td><td>24</td><td>13</td><td>6</td><td>7</td><td>5</td><td>12</td><td>4</td><td>8</td></tr>
    <tr><td>2014</td></tr>
    <tr><td>3 Feb</td><td>Panels/Knesset Channel</td><td>30</td><td>13</td><td>19</td><td>5</td><td>16</td><td>9</td><td>6</td><td>11</td><td>4</td><td>3</td><td>4</td></tr>
    </table>"""
    diagnostics = {}
    rows = parse_wikipedia_archive(
        html,
        "knesset-20",
        "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2015_Israeli_legislative_election",
        diagnostics=diagnostics,
    )
    assert [r["date"] for r in rows] == ["2015-02-03"]
    assert any(r["date"] == "2014-02-03" and r["reason"] == "before_stable_list_cutoff"
               for r in diagnostics["skipped_rows"])


def test_subgroup_poll_is_reported_and_excluded():
    html = """<table>
    <tr><th>Date</th><th>Polling firm</th><th>Likud</th><th>Labor</th><th>Blue &amp; White</th><th>Kulanu</th><th>Raam-Balad</th><th>Shas</th><th>UTJ</th><th>URWP</th><th>Yisrael Beitenu</th><th>Meretz</th><th>Hadash-Taal</th><th>New Right</th><th>Gesher</th><th>Zehut</th></tr>
    <tr><td>31 Mar 2019</td><td>Panels/National Union of Students</td><td>13</td><td>14</td><td>47</td><td>0</td><td>0</td><td>0</td><td>0</td><td>7</td><td>0</td><td>15</td><td>0</td><td>7</td><td>0</td><td>17</td></tr>
    </table>"""
    diagnostics = {}
    rows = parse_wikipedia_archive(
        html,
        "knesset-21",
        "https://en.wikipedia.org/wiki/Opinion_polling_for_the_April_2019_Israeli_legislative_election",
        diagnostics=diagnostics,
    )
    assert rows == []
    assert any(r["reason"] == "non_general_population" for r in diagnostics["skipped_rows"])


def test_target_aliases_from_older_archives_are_resolved():
    assert resolve_pollster("Maariv/Maagar") == "maagar_mohot"
    assert resolve_pollster("Reshet Bet/Meno Geva") == "midgam_geva"
