"""Render a chat message as a Telegram-ready WEBP sticker.

Two shapes: a quote bubble (avatar + coloured name + wrapped text) for text messages,
and a plain resize for images. Telegram wants one side exactly 512 px and the other
at most 512 px; both renderers return images that satisfy that.

Fonts are DejaVu Sans from matplotlib's bundled data (Latin + Cyrillic), so no system
fonts are needed in the slim Docker image. Glyphs it lacks (most emoji) render as boxes.
"""

import io
import os
from dataclasses import dataclass

import matplotlib
from PIL import Image, ImageDraw, ImageFont

STICKER_SIDE = 512

_FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
_REGULAR = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_BOLD = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")

# Telegram's peer colours, indexed by user id like the official clients do.
NAME_COLORS = ["#ff7a6b", "#faa774", "#a695e7", "#7bc862", "#6ec9cb", "#65aadd", "#ee7aae"]
_BUBBLE = "#1e2c3a"
_TEXT = "#ffffff"

# Layout, in pixels at render scale (rendered big then downscaled for smooth edges).
_SCALE = 2
_AVATAR = 56 * _SCALE
_GAP = 8 * _SCALE
_PAD = 12 * _SCALE
_RADIUS = 18 * _SCALE
_NAME_SIZE = 18 * _SCALE
_TEXT_SIZE = 20 * _SCALE
_LINE_SPACING = 6 * _SCALE
_MAX_TEXT_WIDTH = 380 * _SCALE
_MAX_LINES = 18


@dataclass(frozen=True)
class QuoteInput:
    name: str
    text: str
    color_seed: int = 0
    avatar: bytes | None = None


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap by rendered width; keeps explicit newlines, splits over-long words."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split(" "):
            candidate = f"{current} {word}" if current else word
            if font.getlength(candidate) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = ""
            # Break a word that is wider than a whole line on its own.
            for ch in word:
                if current and font.getlength(current + ch) > max_width:
                    lines.append(current)
                    current = ""
                current += ch
        lines.append(current)
    return lines


def _truncate(lines: list[str], font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    if len(lines) <= _MAX_LINES:
        return lines
    kept = lines[:_MAX_LINES]
    last = kept[-1]
    while last and font.getlength(last + "…") > max_width:
        last = last[:-1]
    kept[-1] = last + "…"
    return kept


def _avatar_image(quote: QuoteInput) -> Image.Image:
    size = _AVATAR
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)

    if quote.avatar:
        try:
            src = Image.open(io.BytesIO(quote.avatar)).convert("RGB")
            side = min(src.size)
            left, top = (src.width - side) // 2, (src.height - side) // 2
            src = src.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
            out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            out.paste(src, (0, 0), mask)
            return out
        except Exception:  # a broken photo falls back to initials
            pass

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    color = NAME_COLORS[quote.color_seed % len(NAME_COLORS)]
    ImageDraw.Draw(out).ellipse((0, 0, size - 1, size - 1), fill=color)
    initial = (quote.name.strip()[:1] or "?").upper()
    font = ImageFont.truetype(_BOLD, size // 2)
    ImageDraw.Draw(out).text((size / 2, size / 2), initial, font=font, fill=_TEXT, anchor="mm")
    return out


def _fit_sticker(img: Image.Image) -> Image.Image:
    """Scale so the longer side is exactly STICKER_SIDE."""
    ratio = STICKER_SIDE / max(img.size)
    w = max(1, min(STICKER_SIDE, round(img.width * ratio)))
    h = max(1, min(STICKER_SIDE, round(img.height * ratio)))
    return img.resize((w, h), Image.LANCZOS)


def _to_webp(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=90, method=6)
    return buf.getvalue()


def render_quote(quote: QuoteInput) -> bytes:
    name_font = ImageFont.truetype(_BOLD, _NAME_SIZE)
    text_font = ImageFont.truetype(_REGULAR, _TEXT_SIZE)

    name = quote.name.strip() or "Deleted Account"
    while name and name_font.getlength(name) > _MAX_TEXT_WIDTH:
        name = name[:-1]
    lines = _truncate(wrap_text(quote.text, text_font, _MAX_TEXT_WIDTH), text_font, _MAX_TEXT_WIDTH)

    name_h = name_font.getbbox("Ag")[3]
    line_h = text_font.getbbox("Ag")[3] + _LINE_SPACING
    content_w = max([name_font.getlength(name)] + [text_font.getlength(ln) for ln in lines])
    bubble_w = int(content_w) + 2 * _PAD
    bubble_h = 2 * _PAD + name_h + _LINE_SPACING + line_h * len(lines) - _LINE_SPACING

    width = _AVATAR + _GAP + bubble_w
    height = max(_AVATAR, bubble_h)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Avatar sits at the bottom, next to the bubble's tail, like in Telegram.
    img.alpha_composite(_avatar_image(quote), (0, height - _AVATAR))

    bx = _AVATAR + _GAP
    by = height - bubble_h
    draw.rounded_rectangle((bx, by, bx + bubble_w, by + bubble_h), _RADIUS, fill=_BUBBLE)

    color = NAME_COLORS[quote.color_seed % len(NAME_COLORS)]
    draw.text((bx + _PAD, by + _PAD), name, font=name_font, fill=color)
    y = by + _PAD + name_h + _LINE_SPACING
    for line in lines:
        draw.text((bx + _PAD, y), line, font=text_font, fill=_TEXT)
        y += line_h

    return _to_webp(_fit_sticker(img))


def render_image(data: bytes) -> bytes:
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGBA")
    return _to_webp(_fit_sticker(img))
