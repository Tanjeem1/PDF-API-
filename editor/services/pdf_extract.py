import logging

import fitz

logger = logging.getLogger(__name__)


def extract_pages(pdf_bytes: bytes) -> tuple[list[list[str]], list[tuple[float, float]]]:
    """Return (pages_of_blocks, page_sizes) using reading-order blocks."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages: list[list[str]] = []
        sizes: list[tuple[float, float]] = []
        for page in doc:
            sizes.append((float(page.rect.width), float(page.rect.height)))
            raw_blocks = page.get_text("blocks") or []
            # block: (x0, y0, x1, y1, text, block_no, block_type)
            text_blocks = [
                b for b in raw_blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()
            ]
            text_blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
            pages.append([" ".join(b[4].split()) for b in text_blocks])
        return pages, sizes
    finally:
        doc.close()


def has_extractable_text(pages: list[list[str]]) -> bool:
    return any(block.strip() for page in pages for block in page)
