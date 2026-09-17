from scripts.build_historical_dataset import parse_archive

def test_archive_parser_normalizes_known_pollster_and_parties():
    html='''<table><tr><th>תאריך</th><th>כלי תקשורת</th><th>עורך משאלים</th><th>הליכוד</th><th>יש עתיד</th><th>ש״ס</th><th>יהדות התורה</th><th>הציונות הדתית</th><th>המחנה הממלכתי</th><th>ישראל ביתנו</th><th>רע״מ</th><th>חדש תע״ל</th><th>העבודה</th></tr><tr><td>28/10/2022</td><td>חדשות 12</td><td>מנו גבע</td><td>32</td><td>24</td><td>11</td><td>7</td><td>14</td><td>12</td><td>6</td><td>5</td><td>5</td><td>4</td></tr></table>'''
    rows=parse_archive(html,"knesset-25","https://example.test/archive")
    assert len(rows)==1
    assert rows[0]["pollster"]=="midgam_geva"
    assert rows[0]["parties"]["likud"]==32
    assert sum(rows[0]["parties"].values())==120

def test_archive_parser_rejects_incomplete_seat_vector():
    html='''<table><tr><th>תאריך</th><th>עורך משאלים</th><th>הליכוד</th></tr><tr><td>28/10/2022</td><td>מנו גבע</td><td>32</td></tr></table>'''
    assert parse_archive(html,"knesset-25","https://example.test/archive")==[]


def test_english_archive_parser_supports_older_midgam():
    html='''<table><tr><th>Date</th><th>Polling firm</th><th>Publisher</th><th>Likud</th><th>Blue &amp; White</th><th>Joint List</th><th>Shas</th><th>UTJ</th><th>Yisrael Beitenu</th><th>Yamina</th><th>Labor-Gesher-Meretz</th></tr><tr><td>28 Feb 2020</td><td>Midgam</td><td>Channel 12</td><td>36</td><td>33</td><td>15</td><td>9</td><td>7</td><td>7</td><td>6</td><td>7</td></tr></table>'''
    from scripts.build_historical_dataset import parse_wikipedia_archive
    rows=parse_wikipedia_archive(html,"knesset-23","https://example.test/2020")
    assert len(rows)==1
    assert rows[0]["pollster"]=="midgam_geva"
    assert sum(rows[0]["parties"].values())==120

def test_old_history_is_configured_through_2015():
    from scripts.build_historical_dataset import SOURCES
    elections={s["election"] for s in SOURCES}
    assert {"knesset-20","knesset-21","knesset-22","knesset-23","knesset-24","knesset-25"} <= elections
