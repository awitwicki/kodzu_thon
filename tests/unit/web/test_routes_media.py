import pytest

from kodzu_thon.web.routes.media import INLINE_TYPES, safe_filename


def test_inline_allow_list_is_exactly_the_spec_list():
    expected = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "video/mp4",
        "video/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
    }
    assert expected == INLINE_TYPES


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (None, "blob-7"),
        ("", "blob-7"),
        ("report final.pdf", "report_final.pdf"),
        ("../../etc/passwd", "etc_passwd"),
        ('evil"; rm -rf /', "evil_rm_-rf"),
        ("x" * 300 + ".pdf", "x" * 100),
        ("...", "blob-7"),
    ],
)
def test_safe_filename(name, expected):
    assert safe_filename(name, 7) == expected


async def test_media_requires_login(client, fake_repo):
    fake_repo.add_blob(id=1, mime_type="image/jpeg", data=b"jpg")
    r = await client.get("/media/1")
    assert r.status_code == 303 and r.headers["location"] == "/login"


async def test_inline_types_are_served_inline(authed_client, fake_repo):
    fake_repo.add_blob(id=1, mime_type="image/jpeg", data=b"\xff\xd8jpg")
    r = await authed_client.get("/media/1")
    assert r.status_code == 200 and r.content == b"\xff\xd8jpg"
    assert r.headers["content-type"] == "image/jpeg"
    assert "content-disposition" not in r.headers
    assert r.headers["cache-control"] == "private, max-age=86400"
    assert r.headers["x-content-type-options"] == "nosniff"


async def test_other_types_are_attachments(authed_client, fake_repo):
    fake_repo.add_blob(id=2, mime_type="application/pdf", data=b"%PDF")
    r = await authed_client.get("/media/2?filename=report final.pdf")
    assert r.status_code == 200 and r.content == b"%PDF"
    assert r.headers["content-type"] == "application/octet-stream"
    assert r.headers["content-disposition"] == 'attachment; filename="report_final.pdf"'
    r = await authed_client.get("/media/2")
    assert r.headers["content-disposition"] == 'attachment; filename="blob-2"'


async def test_svg_and_html_are_never_inline(authed_client, fake_repo):
    fake_repo.add_blob(id=3, mime_type="image/svg+xml", data=b"<svg/>")
    fake_repo.add_blob(id=4, mime_type="text/html", data=b"<script>1</script>")
    for blob_id in (3, 4):
        r = await authed_client.get(f"/media/{blob_id}")
        assert r.headers["content-type"] == "application/octet-stream"
        assert r.headers["content-disposition"].startswith("attachment;")


async def test_missing_and_invalid_ids(authed_client):
    assert (await authed_client.get("/media/999")).status_code == 404
    assert (await authed_client.get("/media/0")).status_code == 422
    assert (await authed_client.get("/media/abc")).status_code == 422
    assert (await authed_client.get("/media/1?filename=" + "a" * 256)).status_code == 422
