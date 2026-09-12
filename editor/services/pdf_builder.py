import html
import logging
import os
import tempfile
from pathlib import Path

import fitz
from django.conf import settings

logger = logging.getLogger(__name__)

_FONT_BN = "NotoSansBengali-Regular.ttf"
_FONT_LATIN = "NotoSans-Regular.ttf"


def _font_path(filename: str) -> Path:
    path = settings.FONTS_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required font missing: {path}")
    return path


def _css() -> str:
    return f"""
    @font-face {{
        font-family: NotoBengali;
        src: url({_FONT_BN});
    }}
    @font-face {{
        font-family: NotoSans;
        src: url({_FONT_LATIN});
    }}
    body {{
        font-family: NotoBengali, NotoSans, sans-serif;
        font-size: 12pt;
        line-height: 1.55;
        color: #111111;
    }}
    p {{
        margin: 0 0 10pt 0;
    }}
    """


def _blocks_to_html(blocks: list[str]) -> str:
    if not blocks:
        return "<p></p>"
    parts = []
    for block in blocks:
        escaped = html.escape(block, quote=True).replace("\n", "<br/>")
        parts.append(f"<p>{escaped}</p>")
    return "".join(parts)


def build_translated_pdf(
    pages: list[list[str]],
    page_sizes: list[tuple[float, float]],
) -> bytes:
    """Build a new PDF from translated blocks. Uses MuPDF Story so Bangla shapes."""
    _font_path(_FONT_BN)
    _font_path(_FONT_LATIN)
    archive = fitz.Archive(str(settings.FONTS_DIR))
    css = _css()

    fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    writer = None
    try:
        writer = fitz.DocumentWriter(tmp_path)
        for blocks, (width, height) in zip(pages, page_sizes):
            story = fitz.Story(
                html=_blocks_to_html(blocks),
                user_css=css,
                archive=archive,
            )
            mediabox = fitz.Rect(0, 0, width, height)
            where = mediabox + (48, 48, -48, -48)
            more = True
            while more:
                device = writer.begin_page(mediabox)
                more, _filled = story.place(where)
                story.draw(device)
                writer.end_page()
        writer.close()
        writer = None
        return Path(tmp_path).read_bytes()
    finally:
        if writer is not None:
            try:
                writer.close()
            except Exception:
                logger.debug("DocumentWriter already closed")
        try:
            os.unlink(tmp_path)
        except OSError:
            logger.debug("Temp PDF already removed: %s", tmp_path)
