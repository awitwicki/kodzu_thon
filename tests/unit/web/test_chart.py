from datetime import date

from kodzu_thon.web.chart import DOWN, MIN_BAR, UP, WIDTH, activity_chart


def test_activity_chart_scales_each_series_to_its_own_peak():
    rows = [
        {"kind": "sent", "day": date(2026, 9, 1), "n": 200},
        {"kind": "sent", "day": date(2026, 9, 3), "n": 100},
        {"kind": "sent", "day": date(2026, 9, 4), "n": 1},
        {"kind": "deleted", "day": date(2026, 9, 3), "n": 4},
    ]
    chart = activity_chart(rows, start=date(2026, 9, 1), end=date(2026, 9, 4))
    assert chart["days"] == 4 and len(chart["bars"]) == 4
    assert (chart["total_sent"], chart["total_deleted"]) == (301, 4)
    assert (chart["peak_sent"], chart["peak_deleted"]) == (200, 4)
    first, empty, third, tiny = chart["bars"]
    assert (first["up"], first["up_y"], first["down"]) == (UP, 0, 0)
    assert (empty["up"], empty["down"]) == (0, 0)
    assert (third["up"], third["down"]) == (UP / 2, DOWN)
    assert tiny["up"] == MIN_BAR  # one message stays visible beside a 200-message day
    assert third["label"] == "3 Sep: 100 messages, 4 deleted"
    assert chart["bars"][-1]["x"] + chart["bar_width"] <= WIDTH


def test_activity_chart_with_no_rows_is_all_zero():
    chart = activity_chart([], start=date(2026, 9, 1), end=date(2026, 9, 30))
    assert chart["total_sent"] == 0 and chart["total_deleted"] == 0
    assert all(b["up"] == 0 and b["down"] == 0 for b in chart["bars"])
