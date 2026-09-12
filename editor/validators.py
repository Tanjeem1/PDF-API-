import logging

import fitz
from django.conf import settings
from rest_framework import serializers

from editor.exceptions import BadPDFError, FileTooLargeError

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"


def normalize_hex_color(value: str) -> str:
    raw = (value or "").strip()
    if raw.startswith("#"):
        raw = raw[1:]
    if len(raw) != 6 or any(c not in "0123456789abcdefABCDEF" for c in raw):
        raise serializers.ValidationError(
            "Color must be a hex string like #RRGGBB or RRGGBB."
        )
    return f"#{raw.upper()}"


def hex_to_rgb01(color: str) -> tuple[float, float, float]:
    value = color.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def validate_uploaded_pdf(uploaded) -> None:
    """Reject spoofed extensions, encrypted files, empty docs, and huge page counts."""
    size = getattr(uploaded, "size", None)
    if size is not None and size > settings.MAX_UPLOAD_BYTES:
        raise FileTooLargeError()

    header = uploaded.read(5)
    uploaded.seek(0)
    if header != PDF_MAGIC:
        raise BadPDFError("File is not a valid PDF")

    payload = uploaded.read()
    uploaded.seek(0)

    doc = None
    try:
        doc = fitz.open(stream=payload, filetype="pdf")
    except Exception as exc:
        logger.info("Rejected unreadable upload: %s", exc)
        raise BadPDFError("File is not a valid PDF") from exc

    try:
        if doc.is_encrypted and not doc.authenticate(""):
            raise BadPDFError("PDF is encrypted or password-protected")
        if doc.page_count == 0:
            raise BadPDFError("PDF has no pages")
        if doc.page_count > settings.MAX_PDF_PAGES:
            raise BadPDFError(f"PDF exceeds the maximum of {settings.MAX_PDF_PAGES} pages")
    finally:
        if doc is not None:
            doc.close()
        uploaded.seek(0)
