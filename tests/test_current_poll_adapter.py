from polltrust.adapters.wikipedia_2026 import (
    parse_current_polling_page,
    parse_poll_date,
    parse_seat_cell,
    resolve_pollster,
)


SOURCE = "https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Israeli_legislative_election"


def test_current_aliases_are_conservative_and_complete():
    assert resolve_pollster("Midgam R&C") == "midgam_geva"
    assert resolve_pollster("Kantar") == "kantar_hasid"
    assert resolve_pollster("LRI+P4A") == "lazar_research"
    assert resolve_pollster("Maagar Mochot") == "maagar_mohot"
    assert resolve_pollster("Direct Polls") == "direct_polls_sharon"
    assert resolve_pollster("SF+ND") == "next_data_filber"
    assert resolve_pollster("MP+TM+SN+A") == "hamadad_consortium"
    assert resolve_pollster("MP, M, SN, A") == "hamadad_consortium"
    assert resolve_pollster("Yossi Tatika") == "tatika"
    assert resolve_pollster("Smith") is None


def test_current_date_ranges_use_end_of_fieldwork():
    assert parse_poll_date("9–10 Sep") == "2026-09-10"
    assert parse_poll_date("15 Sep") == "2026-09-15"


def test_current_seat_cell_distinguishes_seats_from_below_threshold_percent():
    assert parse_seat_cell("4") == 4
    assert parse_seat_cell("4 (3.9%)") == 4
    assert parse_seat_cell("(3.1%)") == 0
    assert parse_seat_cell("(<1%)") == 0
    assert parse_seat_cell("—N/a") == 0


def test_current_table_parser_imports_only_post_closure_target_pollsters():
    html = """<table>
    <tr><th>Fieldwork date</th><th>Polling firm</th><th>Publisher</th><th>Sample size</th>
    <th>Likud</th><th>Together</th><th>RZP</th><th>Otzma</th><th>Blue & White</th>
    <th>Shas</th><th>UTJ</th><th>Yisrael Beiteinu</th><th>Ra'am</th><th>Joint List</th>
    <th>Dems</th><th>Yashar</th><th>Reserv.</th><th>Amcha Yisrael</th><th>Haredi Public</th>
    <th>Others</th><th>Gov.</th></tr>
    <tr><td>14 Sep</td><td>Midgam R&amp;C</td><td>HaHadashot 12</td><td>502</td>
    <td>20</td><td>13</td><td>5</td><td>6</td><td>(0.5%)</td><td>7</td><td>8</td><td>8</td>
    <td>4</td><td>8</td><td>10</td><td>23</td><td>4</td><td>4</td><td>—N/a</td><td>—N/a</td><td>46</td></tr>
    <tr><td>15 Sep</td><td>SF+ND</td><td>Channel 14</td><td>483</td>
    <td>30</td><td>8</td><td>8</td><td>8</td><td>(0.4%)</td><td>10</td><td>8</td><td>6</td>
    <td>5</td><td>7</td><td>9</td><td>21</td><td>(2.1%)</td><td>(2.3%)</td><td>(0.2%)</td><td>0.3%</td><td>63</td></tr>
    <tr><td>8 Sep</td><td>Kantar</td><td>Kan 11</td><td>551</td>
    <td>20</td><td>13</td><td>6</td><td>7</td><td>0</td><td>7</td><td>8</td><td>7</td>
    <td>6</td><td>7</td><td>8</td><td>23</td><td>4</td><td>4</td><td>0</td><td>0</td><td>48</td></tr>
    <tr><td>15 Sep</td><td>Smith</td><td>Maariv</td><td>500</td>
    <td>20</td><td>13</td><td>5</td><td>6</td><td>0</td><td>7</td><td>8</td><td>8</td>
    <td>4</td><td>8</td><td>10</td><td>23</td><td>4</td><td>4</td><td>0</td><td>0</td><td>46</td></tr>
    </table>"""
    rows = parse_current_polling_page(html, SOURCE)
    assert [(r["pollster"], r["date"]) for r in rows] == [
        ("next_data_filber", "2026-09-15"),
        ("midgam_geva", "2026-09-14"),
    ]
    assert all(sum(r["parties"].values()) == 120 for r in rows)
    assert rows[0]["outlet"] == "Channel 14"
