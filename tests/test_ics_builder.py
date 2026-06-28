from datetime import date

from engines import ics_builder


def _fake_profile():
    return {"meta": {"name": "测试用户"}}


def _fake_personalized(day):
    day_num = int(day["date"][-2:])
    if day_num in {3, 8, 18, 35}:
        return {
            "date": day["date"],
            "score": 88,
            "tier": "大吉",
            "personal_yi": [{"item": "签约"}, {"item": "出行"}],
            "personal_ji": [{"item": "无"}],
            "flags": {},
        }
    if day_num in {5, 12, 25, 40}:
        return {
            "date": day["date"],
            "score": 22,
            "tier": "忌",
            "personal_yi": [{"item": "整理"}],
            "personal_ji": [{"item": "诸事不宜"}, {"item": "付款"}],
            "flags": {"冲日主": True, "冲流年太岁": False},
        }
    return {
        "date": day["date"],
        "score": 50,
        "tier": "平",
        "personal_yi": [],
        "personal_ji": [],
        "flags": {},
    }


def _patch_calendar(monkeypatch):
    monkeypatch.setattr(
        "engines.daily.build",
        lambda date_str: {"date": date_str, "ganzhi": {"day": "甲子"}},
    )
    monkeypatch.setattr("engines.personalize.build", lambda profile, day: _fake_personalized(day))
    monkeypatch.setattr(ics_builder, "_is_destined_moment", lambda profile, day: False)


def test_preview_is_30_days_key_subset_and_contains_good_and_avoid(monkeypatch):
    _patch_calendar(monkeypatch)

    events = ics_builder.preview_days(
        _fake_profile(),
        start_date=date(2026, 1, 1),
    )

    assert 3 <= len(events) <= 4
    assert all("2026-01-01" <= e["date"] < "2026-01-31" for e in events)
    assert any(e["event_kind"] == "good" for e in events)
    assert any(e["event_kind"] == "avoid" for e in events)
    assert all(e["date"] != "2026-02-05" for e in events)


def test_collect_events_for_export_keeps_every_day(monkeypatch):
    _patch_calendar(monkeypatch)

    events = ics_builder.collect_events(
        _fake_profile(),
        days_ahead=30,
        start_date=date(2026, 1, 1),
    )

    assert len(events) == 30
    assert any(e["tier"] == "大吉" for e in events)
    assert any(e["tier"] == "避凶提醒" for e in events)
    assert any(e["tier"] == "平" for e in events)


def test_ics_summary_is_short_split_tracks_and_has_no_alarms():
    content = ics_builder.build_ics(
        _fake_profile(),
        days_ahead=30,
        start_date=date(2026, 7, 1),
        events=[
            {
                "date": "2026-01-05",
                "score": 20,
                "tier": "避凶提醒",
                "event_kind": "avoid",
                "is_destined": False,
                "personal_yi": [{"item": "整理"}],
                "personal_ji": [{"item": "诸事不宜"}, {"item": "付款"}],
                "flags": {},
            },
            {
                "date": "2026-01-08",
                "score": 90,
                "tier": "大吉",
                "event_kind": "good",
                "is_destined": False,
                "personal_yi": [{"item": "签约"}, {"item": "出行"}],
                "personal_ji": [{"item": "无"}],
                "flags": {},
            },
        ],
    )

    assert content.count("BEGIN:VEVENT") == 4
    assert content.count("DTSTART;VALUE=DATE:20260105") == 2
    assert "SUMMARY:忌付款" in content
    assert "SUMMARY:宜整理" in content
    assert "SUMMARY:宜签约.出门" in content
    assert "SUMMARY:续日历" not in content
    assert "续期" not in content
    assert "BEGIN:VALARM" not in content
    assert "END:VALARM" not in content
    assert "避凶提醒" not in "\n".join(line for line in content.splitlines() if line.startswith("SUMMARY:"))
    assert "大吉" not in "\n".join(line for line in content.splitlines() if line.startswith("SUMMARY:"))
    assert "⭐" not in content
    assert "⚠" not in content
    assert "⏰" not in content
    assert "忌无" not in content
    assert "DESCRIPTION:【今日宜】整理" in content
    assert "DESCRIPTION:【今日忌】付款" in content
    assert "DESCRIPTION:【今日宜】签约、出门" in content
    assert "DESCRIPTION:【今日忌】冲动决定、大额付款、争执" in content
    assert "DESCRIPTION:【今日宜】整理\\n【今日忌】付款" not in content
    assert "DESCRIPTION:【今日宜】签约、出门\\n【今日忌】冲动决定、大额付款、争执" not in content
    assert "：" not in "\n".join(line for line in content.splitlines() if line.startswith("DESCRIPTION:"))
    assert "用神" not in content
    assert "传统忌日" not in content


def test_preview_lines_filters_empty_and_noisy_items():
    lines = ics_builder.preview_lines([
        {
            "date": "2026-01-05",
            "tier": "避凶提醒",
            "personal_yi": [{"item": "整理"}],
            "personal_ji": [{"item": "诸事不宜"}, {"item": "付款"}],
        },
        {
            "date": "2026-01-08",
            "tier": "大吉",
            "personal_yi": [{"item": "签约"}],
            "personal_ji": [{"item": "无"}],
        },
    ])

    assert lines == [
        "2026-01-05  避凶提醒  宜整理  忌付款",
        "2026-01-08  大吉  宜签约  忌搬家、装修",
    ]


def test_flat_day_gets_yi_and_ji_tracks(monkeypatch):
    _patch_calendar(monkeypatch)

    content = ics_builder.build_ics(
        _fake_profile(),
        start_date=date(2026, 1, 1),
    )

    assert content.count("BEGIN:VEVENT") == 60
    assert content.count("DTSTART;VALUE=DATE:20260101") == 2
    assert "SUMMARY:宜整理" in content
    assert "SUMMARY:忌搬家.装修" in content
