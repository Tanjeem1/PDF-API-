import logging

import fitz
from django.conf import settings

from editor.validators import hex_to_rgb01

logger = logging.getLogger(__name__)

MARGIN = 36.0

ALIGN = {
    "left": fitz.TEXT_ALIGN_LEFT,
    "center": fitz.TEXT_ALIGN_CENTER,
    "right": fitz.TEXT_ALIGN_RIGHT,
}

POSITIONS = {
    "top-left": "left",
    "top-center": "center",
    "top-right": "right",
    "center": "center",
    "bottom-left": "left",
    "bottom-center": "center",
    "bottom-right": "right",
}


def _has_bengali(text: str) -> bool:
    return any("\u0980" <= ch <= "\u09FF" for ch in text)


def _fontfile(text: str) -> str:
    fonts = settings.FONTS_DIR
    bengali = fonts / "NotoSansBengali-Regular.ttf"
    latin = fonts / "NotoSans-Regular.ttf"
    if _has_bengali(text) and bengali.is_file():
        return str(bengali)
    if latin.is_file():
        return str(latin)
    return str(bengali)


def watermark_rect(page_rect: fitz.Rect, position: str, margin: float = MARGIN) -> fitz.Rect:
    """Return the insert_textbox rect for a named anchor. Origin is top-left."""
    if position not in POSITIONS:
        raise ValueError(f"Unknown position: {position}")

    h = page_rect.height
    left = page_rect.x0 + margin
    right = page_rect.x1 - margin

    if position == "center":
        box_h = max(140.0, h * 0.3)
        mid = page_rect.y0 + h / 2.0
        return fitz.Rect(left, mid - box_h / 2.0, right, mid + box_h / 2.0)

    box_h = max(64.0, min(110.0, h * 0.14))
    if position.startswith("top-"):
        top = page_rect.y0 + margin
        return fitz.Rect(left, top, right, top + box_h)

    bottom = page_rect.y1 - margin
    return fitz.Rect(left, bottom - box_h, right, bottom)


def _fontsize(page_rect: fitz.Rect, position: str) -> float:
    if position == "center":
        return max(52.0, min(96.0, page_rect.width / 8.0))
    return max(24.0, min(44.0, page_rect.width / 14.0))


def _fitting_fontsize(text: str, fontfile: str, rect: fitz.Rect, start: float) -> float:
    font = fitz.Font(fontfile=fontfile)
    size = start
    max_width = max(8.0, rect.width * 0.92)
    max_height = max(8.0, rect.height * 0.7)
    while size >= 10:
        if font.text_length(text, fontsize=size) <= max_width and size * 1.35 <= max_height:
            return size
        size -= 2
    return 10.0


def apply_watermark(
    pdf_bytes: bytes,
    text: str,
    position: str,
    opacity: float,
    color: str,
) -> bytes:
    rgb = hex_to_rgb01(color)
    fontfile = _fontfile(text)
    fontname = "nnotowm"

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page in doc:
            rect = watermark_rect(page.rect, position)
            align = ALIGN[POSITIONS[position]]
            fontsize = _fitting_fontsize(
                text, fontfile, rect, _fontsize(page.rect, position)
            )
            leftover = page.insert_textbox(
                rect,
                text,
                fontsize=fontsize,
                fontname=fontname,
                fontfile=fontfile,
                color=rgb,
                fill_opacity=float(opacity),
                align=align,
                overlay=True,
            )
            if leftover < 0:
                logger.warning("Watermark text did not fit on a page")
        return doc.tobytes()
    finally:
        doc.close()
