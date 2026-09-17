from __future__ import annotations

from datetime import date, timedelta


def build_demo_raw():
    active = [
        {"id":"midgam_geva","name_he":"מדגם / מנו גבע","outlet_he":"חדשות 12"},
        {"id":"kantar_hasid","name_he":"קנטאר / דודי חסיד","outlet_he":"כאן 11"},
        {"id":"lazar_research","name_he":"לזר מחקרים / מנחם לזר","outlet_he":"מעריב"},
        {"id":"maagar_mohot","name_he":"מאגר מוחות / יצחק כ״ץ","outlet_he":"כלי תקשורת נוכחי"},
        {"id":"direct_polls_sharon","name_he":"Direct Polls / צוריאל שרון","outlet_he":"i24NEWS","lineage_note_he":"חלק מהערכת האמינות ההיסטורית מבוסס על התקופה המשותפת של Direct Polls. משקל היסטוריה זו מופחת ויורד ככל שמצטברים נתונים עצמאיים."},
        {"id":"next_data_filber","name_he":"NEXT DATA / שלמה פילבר","outlet_he":"ערוץ 14","lineage_note_he":"חלק מהערכת האמינות ההיסטורית מבוסס על התקופה המשותפת של Direct Polls. משקל היסטוריה זו מופחת ויורד ככל שמצטברים נתונים עצמאיים."},
        {"id":"hamadad_consortium","name_he":"המדד / קונסורציום חדשות 13","outlet_he":"חדשות 13"},
        {"id":"tatika","name_he":"יוסי טאטיקה / Tatika Research & Media","outlet_he":"כלי תקשורת נוכחי"}
    ]
    historical=["midgam_geva","kantar_hasid","lazar_research","maagar_mohot","direct_polls_shared"]
    elections=[{"id":"demo1","date":"2020-03-02","result":{"party_a":45,"party_b":40,"party_c":35}},{"id":"demo2","date":"2021-03-23","result":{"party_a":42,"party_b":43,"party_c":35}},{"id":"demo3","date":"2022-11-01","result":{"party_a":40,"party_b":44,"party_c":36}}]
    polls=[]
    offsets={"midgam_geva":1,"kantar_hasid":2,"lazar_research":3,"maagar_mohot":4,"direct_polls_shared":2}
    for e in elections:
        ed=date.fromisoformat(e["date"])
        for pid in historical:
            for horizon in (60,30,7,1):
                shift=offsets[pid] + (1 if horizon >= 30 else 0)
                result=e["result"]
                parties={"party_a":result["party_a"]+shift,"party_b":result["party_b"]-shift,"party_c":result["party_c"]}
                polls.append({"pollster":pid,"election":e["id"],"date":(ed-timedelta(days=horizon)).isoformat(),"source":"demo://synthetic","parties":parties})
    return {"schema_version":1,"as_of":"2026-09-18T00:00:00+03:00","demo_mode":True,"active_pollsters":active,"historical_pollsters":historical,"elections":elections,"polls":polls,"analysis":{"max_days_before":120,"max_staleness_days":45,"truth_bias_bloc_parties":["party_a"],"clusters":{"midgam_geva":"a","kantar_hasid":"a","lazar_research":"b","maagar_mohot":"b","direct_polls_shared":"c"}},"shared_prior":{"historical_id":"direct_polls_shared","targets":["direct_polls_sharon","next_data_filber"],"discount":0.5}}
