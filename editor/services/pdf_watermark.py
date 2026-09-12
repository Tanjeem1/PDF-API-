import logging

import fitz
from django.conf import settings

from editor.validators import hex_to_rgb01

logger = logging.getLogger(__name__)

MARGIN = 36.0
BOX_HEIGHT = 48.0

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


def watermark_rect(page_rect: fitz.Rect, position: str, margin: float = MARGIN) -> fitz.Rect:
    """Return the insert_textbox rect for a named anchor. Origin is top-left."""
    if position not in POSITIONS:
        raise ValueError(f"Unknown position: {position}")

    w, h = page_rect.width, page_rect.height
    box_h = min(BOX_HEIGHT, max(24.0, h * 0.08))
    left = page_rect.x0 + margin
    right = page_rect.x1 - margin

    if position.startswith("top-"):
        top = page_rect.y0 + margin
        bottom = top + box_h
    elif position.startswith("bottom-"):
        bottom = page_rect.y1 - margin
        top = bottom - box_h
    else:  # center
        mid = page_rect.y0 + h / 2.0
        top = mid - box_h / 2.0
        bottom = mid + box_h / 2.0

    return fitz.Rect(left, top, right, bottom)


def _fontsize(page_rect: fitz.Rect) -> float:
    return max(12.0, min(28.0, page_rect.width / 22.0))


def apply_watermark(
    pdf_bytes: bytes,
    text: str,
    position: str,
    opacity: float,
    color: str,
) -> bytes:
    rgb = hex_to_rgb01(color)
    font_bn = settings.FONTS_DIR / "NotoSansBengali-Regular.ttf"
    font_latin = settings.FONTS_DIR / "NotoSans-Regular.ttf"

    fontfile = str(font_bn if font_bn.is_file() else font_latin)
    fontname = "nnotowm"

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        for page in doc:
            rect = watermark_rect(page.rect, position)
            align = ALIGN[POSITIONS[position]]
            page.insert_textbox(
                rect,
                text,
                fontsize=_fontsize(page.rect),
                fontname=fontname,
                fontfile=fontfile,
                color=rgb,
                fill_opacity=float(opacity),
                align=align,
                overlay=True,
            )
        return doc.tobytes()
    finally:
        doc.close()
