"""Geometry for the chat page's activity chart: messages per day drawn upward from a
baseline, deletions per day downward. Rendered as inline SVG by the template (there is no
JavaScript), so everything the template needs is precomputed here."""

from datetime import date, timedelta

WIDTH = 280
UP = 72  # tallest "messages" bar
DOWN = 24  # tallest "deleted" bar
MIN_BAR = 1.5  # a non-zero day stays visible next to a very busy one


def _height(value: int, peak: int, full: int) -> float:
    if not value or not peak:
        return 0.0
    return round(max(full * value / peak, MIN_BAR), 1)


def activity_chart(rows: list[dict], *, start: date, end: date) -> dict:
    """`rows` are Repository.chat_activity rows; days without a row count as zero."""
    counts = {"sent": {}, "deleted": {}}
    for row in rows:
        counts[row["kind"]][row["day"]] = row["n"]
    days = [start + timedelta(days=n) for n in range((end - start).days + 1)]
    sent = [counts["sent"].get(d, 0) for d in days]
    deleted = [counts["deleted"].get(d, 0) for d in days]
    peak_sent, peak_deleted = max(sent), max(deleted)
    step = WIDTH / len(days)
    bar_width = round(step * 0.7, 2)
    bars = []
    for i, day in enumerate(days):
        up = _height(sent[i], peak_sent, UP)
        bars.append(
            {
                "x": round(i * step + (step - bar_width) / 2, 2),
                "slot_x": round(i * step, 2),
                "up": up,
                "up_y": round(UP - up, 1),
                "down": _height(deleted[i], peak_deleted, DOWN),
                "label": f"{day.day} {day:%b}: {sent[i]} messages, {deleted[i]} deleted",
            }
        )
    return {
        "width": WIDTH,
        "height": UP + DOWN + 2,
        "base": UP,
        "slot": round(step, 2),
        "bar_width": bar_width,
        "bars": bars,
        "total_sent": sum(sent),
        "total_deleted": sum(deleted),
        "peak_sent": peak_sent,
        "peak_deleted": peak_deleted,
        "start": start,
        "end": end,
        "days": len(days),
    }
