from datetime import UTC, datetime

from markupsafe import Markup

from kodzu_thon.web.textfmt import (
    display_name,
    escape_like,
    format_text,
    group_albums,
    human_size,
    linkify,
    local_time,
    nl2br,
)


def test_linkify_escapes_html_and_links_http_urls():
    out = linkify("<b>see</b> https://example.com/a?b=1&c=2 and http://x.y/z.")
    assert isinstance(out, Markup)
    assert "&lt;b&gt;see&lt;/b&gt;" in out
    assert '<a href="https://example.com/a?b=1&amp;c=2" rel="noopener noreferrer">' in out
    # trailing punctuation stays outside the link
    assert '<a href="http://x.y/z" rel="noopener noreferrer">http://x.y/z</a>.' in out


def test_linkify_ignores_other_schemes():
    out = str(linkify("javascript:alert(1) ftp://host/file mailto:a@b.c"))
    assert "<a " not in out


def test_linkify_never_emits_raw_quotes_in_href():
    out = str(linkify('http://a.b/"onmouseover="x'))
    assert out.count("<a ") == 1
    assert out.count('"') == 4  # only the href/rel attribute delimiters; the URL's quote is &#34;
    assert 'onmouseover="' not in out


def test_nl2br_and_format_text():
    assert str(nl2br(Markup("a\nb"))) == "a<br>\nb"
    assert str(format_text("x <i>\ny")) == "x &lt;i&gt;<br>\ny"
    assert str(format_text(None)) == ""


def test_escape_like():
    assert escape_like("50% off_now\\") == "50\\% off\\_now\\\\"
    assert escape_like("plain") == "plain"


def test_local_time_converts_to_zone():
    dt = datetime(2026, 9, 13, 10, 0, tzinfo=UTC)
    assert local_time(dt, "Europe/Warsaw") == "2026-09-13 12:00"
    assert local_time(None, "Europe/Warsaw") == ""


def test_human_size():
    assert human_size(None) == ""
    assert human_size(0) == "0 B"
    assert human_size(999) == "999 B"
    assert human_size(1536) == "1.5 KB"
    assert human_size(5 * 1024 * 1024) == "5.0 MB"


def test_display_name():
    assert display_name("Ann", "Lee", "ann") == "Ann Lee"
    assert display_name("Ann", None, "ann") == "Ann"
    assert display_name(None, None, "ann") == "@ann"
    assert display_name(None, None, None) == "unknown"
    assert display_name("", "", "", fallback="deleted account") == "deleted account"


def test_group_albums_groups_consecutive_grouped_ids():
    rows = [
        {"id": 5, "grouped_id": None},
        {"id": 4, "grouped_id": 77},
        {"id": 3, "grouped_id": 77},
        {"id": 2, "grouped_id": None},
        {"id": 1, "grouped_id": 77},  # same id but not consecutive -> separate album
    ]
    assert [[r["id"] for r in album] for album in group_albums(rows)] == [[5], [4, 3], [2], [1]]
    assert group_albums([]) == []
