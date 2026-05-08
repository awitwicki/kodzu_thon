from freezegun import freeze_time

from kodzu_thon.services.year_progress import get_year_progress, progress_bar


def test_progress_bar_zero():
    out = progress_bar(0, 100, length=10)
    assert "----------" in out
    assert "0.00%" in out


def test_progress_bar_full():
    out = progress_bar(100, 100, length=10)
    assert "██████████" in out
    assert "100.00%" in out


@freeze_time("2026-07-02")
def test_get_year_progress_includes_day_of_year():
    out = get_year_progress(20)
    assert "183/365" in out
