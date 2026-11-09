import io

import pytest
from PIL import Image, ImageFont, UnidentifiedImageError

from kodzu_thon.services import quote_sticker as qs


def _open(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    assert img.format == "WEBP"
    return img


def _assert_sticker_size(img: Image.Image) -> None:
    assert max(img.size) == qs.STICKER_SIDE
    assert min(img.size) <= qs.STICKER_SIDE


def test_render_quote_is_sticker_sized_webp():
    img = _open(qs.render_quote(qs.QuoteInput(name="Андрій", text="Привіт, світ!", color_seed=3)))
    _assert_sticker_size(img)


def test_render_quote_long_text_is_truncated_and_still_fits():
    text = "дуже довгий текст " * 500
    img = _open(qs.render_quote(qs.QuoteInput(name="X", text=text)))
    _assert_sticker_size(img)


def test_render_quote_uses_avatar_bytes_and_survives_garbage_avatar():
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "red").save(buf, format="JPEG")
    _assert_sticker_size(_open(qs.render_quote(qs.QuoteInput("A", "hi", avatar=buf.getvalue()))))
    _assert_sticker_size(_open(qs.render_quote(qs.QuoteInput("A", "hi", avatar=b"not an image"))))


def test_render_quote_empty_name():
    _assert_sticker_size(_open(qs.render_quote(qs.QuoteInput(name="", text="hi"))))


def test_wrap_text_keeps_newlines_and_splits_long_words():
    font = ImageFont.truetype(qs._REGULAR, 20)
    lines = qs.wrap_text("a b\n\n" + "x" * 200, font, 100)
    assert lines[:2] == ["a b", ""]
    assert len(lines) > 3
    assert all(font.getlength(ln) <= 100 for ln in lines)


def test_render_image_resizes_to_sticker():
    buf = io.BytesIO()
    Image.new("RGB", (1000, 300), "blue").save(buf, format="PNG")
    img = _open(qs.render_image(buf.getvalue()))
    assert img.size == (512, 154)


def test_render_image_rejects_huge_dimensions_before_decoding(mocker):
    buf = io.BytesIO()
    Image.new("RGB", (100, 100)).save(buf, format="PNG")
    mocker.patch.object(qs, "MAX_IMAGE_PIXELS", 5000)
    with pytest.raises(qs.ImageTooLarge):
        qs.render_image(buf.getvalue())


def test_render_image_rejects_unlisted_formats():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="TIFF")
    with pytest.raises(UnidentifiedImageError):
        qs.render_image(buf.getvalue())
