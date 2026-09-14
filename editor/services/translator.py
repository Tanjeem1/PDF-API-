import logging
import re
import time

import requests
from deep_translator import GoogleTranslator, MyMemoryTranslator
from deep_translator.exceptions import LanguageNotSupportedException
from django.conf import settings

from editor.exceptions import TranslationServiceError

logger = logging.getLogger(__name__)

_CODE_TO_NAME: dict[str, str] | None = None
_NAME_TO_CODE: dict[str, str] | None = None
_MYMEMORY_CODES: dict[str, str] | None = None

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")


def _language_maps() -> tuple[dict[str, str], dict[str, str]]:
    global _CODE_TO_NAME, _NAME_TO_CODE
    if _CODE_TO_NAME is None or _NAME_TO_CODE is None:
        # Local dict — no network. Values are ISO codes, keys are names.
        name_to_code = {
            str(name).strip().lower(): str(code).strip().lower()
            for name, code in GoogleTranslator().get_supported_languages(as_dict=True).items()
        }
        code_to_name = {code: name for name, code in name_to_code.items()}
        _NAME_TO_CODE = name_to_code
        _CODE_TO_NAME = code_to_name
    return _CODE_TO_NAME, _NAME_TO_CODE


def normalize_language_code(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        raise LanguageNotSupportedException(value)
    code_to_name, name_to_code = _language_maps()
    if raw in code_to_name:
        return raw
    if raw in name_to_code:
        return name_to_code[raw]
    # zh-cn style
    compact = raw.replace("_", "-")
    if compact in code_to_name:
        return compact
    raise LanguageNotSupportedException(value)


def chunk_text(text: str, limit: int | None = None) -> list[str]:
    limit = limit or settings.TRANSLATION_CHUNK_CHARS
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    pieces = _SENTENCE_SPLIT.split(text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if len(piece) > limit:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(piece), limit):
                chunks.append(piece[i : i + limit])
            continue
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    return chunks


_MYMEMORY_DEFAULTS = {
    "en": "en-GB",
    "bn": "bn-IN",
    "zh": "zh-CN",
    "hi": "hi-IN",
    "ar": "ar-SA",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
}


def _mymemory_code(code: str) -> str:
    """Map ISO codes like 'en' / 'bn' to MyMemory locales (en-GB, bn-IN)."""
    global _MYMEMORY_CODES
    key = code.strip().lower()
    if _MYMEMORY_CODES is None:
        mapped = dict(_MYMEMORY_DEFAULTS)
        try:
            raw = MyMemoryTranslator(source="en-GB", target="bn-IN").get_supported_languages(
                as_dict=True
            )
            for locale in raw.values():
                locale = str(locale)
                short = locale.split("-", 1)[0].lower()
                mapped.setdefault(short, locale)
                mapped[locale.lower()] = locale
            mapped.update(_MYMEMORY_DEFAULTS)
        except Exception as exc:
            logger.info("MyMemory language list unavailable (%s)", exc)
        _MYMEMORY_CODES = mapped
    if key in _MYMEMORY_CODES:
        return _MYMEMORY_CODES[key]
    if len(key) == 2:
        return f"{key}-{key.upper()}"
    raise LanguageNotSupportedException(code)


def _is_unchanged(original: str, translated: str) -> bool:
    return (translated or "").strip().rstrip(".!?").lower() == (original or "").strip().rstrip(".!?").lower()


def _require_changed(original: str, translated: str, backend: str) -> str:
    if not (translated or "").strip() or _is_unchanged(original, translated):
        raise RuntimeError(f"{backend} returned empty or original text")
    return translated


def _translate_with_google(text: str, source: str, target: str) -> str:
    return _require_changed(
        text, GoogleTranslator(source=source, target=target).translate(text), "GoogleTranslator"
    )


def _translate_with_google_gtx(text: str, source: str, target: str) -> str:
    src = normalize_language_code(source)
    dst = normalize_language_code(target)
    parts: list[str] = []
    for piece in chunk_text(text, 450) or [text]:
        response = requests.get(
            "https://clients5.google.com/translate_a/t",
            params={"client": "dict-chrome-ex", "sl": src, "tl": dst, "q": piece},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            out = data[0][0] if isinstance(data[0], list) else data[0]
        else:
            out = ""
        parts.append(_require_changed(piece, str(out or ""), "GoogleGTX"))
    return " ".join(parts)


def _translate_with_mymemory_http(text: str, source: str, target: str) -> str:
    src = normalize_language_code(source)
    dst = normalize_language_code(target)
    parts: list[str] = []
    for piece in chunk_text(text, 450) or [text]:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": piece, "langpair": f"{src}|{dst}"},
            timeout=20,
        )
        response.raise_for_status()
        out = ((response.json() or {}).get("responseData") or {}).get("translatedText") or ""
        parts.append(_require_changed(piece, out, "MyMemoryHTTP"))
    return " ".join(parts)


def _translate_with_mymemory(text: str, source: str, target: str) -> str:
    src = _mymemory_code(source)
    dst = _mymemory_code(target)
    pieces = chunk_text(text, 450) or [text]
    translator = MyMemoryTranslator(source=src, target=dst)
    out = " ".join(translator.translate(piece) for piece in pieces)
    return _require_changed(text, out, "MyMemory")


def _translate_with_lingva(text: str, source: str, target: str) -> str:
    from requests.utils import quote

    src = normalize_language_code(source)
    dst = normalize_language_code(target)
    url = f"https://lingva.ml/api/v1/{src}/{dst}/{quote(text)}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    out = (response.json() or {}).get("translation") or ""
    return _require_changed(text, out, "Lingva")


def _google_translate(text: str, source: str, target: str) -> str:
    """Try public backends in order. Reject unchanged copy as a failure."""
    errors: list[Exception] = []
    for name, fn in (
        ("GoogleGTX", _translate_with_google_gtx),
        ("MyMemoryHTTP", _translate_with_mymemory_http),
        ("GoogleTranslator", _translate_with_google),
        ("MyMemory", _translate_with_mymemory),
        ("Lingva", _translate_with_lingva),
    ):
        try:
            return fn(text, source, target)
        except Exception as exc:
            errors.append(exc)
            logger.info("%s unavailable (%s)", name, exc)
    raise errors[-1]


def translate_text(text: str, source: str, target: str) -> str:
    chunks = chunk_text(text)
    if not chunks:
        return ""

    translated_parts: list[str] = []
    attempts = settings.TRANSLATION_MAX_ATTEMPTS
    for chunk in chunks:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                translated_parts.append(_google_translate(chunk, source, target))
                last_error = None
                break
            except TranslationServiceError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Translation attempt %s/%s failed: %s", attempt, attempts, exc
                )
                if attempt < attempts:
                    time.sleep(0.4 * attempt)
        if last_error is not None:
            logger.exception("Translation service failed after retries")
            raise TranslationServiceError()
    return " ".join(translated_parts)


def translate_pages(pages: list[list[str]], source: str, target: str) -> list[list[str]]:
    cache: dict[str, str] = {}
    src = normalize_language_code(source)
    dst = normalize_language_code(target)
    out: list[list[str]] = []
    for page in pages:
        joined = "\n\n".join(block for block in page if block.strip())
        if not joined:
            out.append([])
            continue
        if joined not in cache:
            cache[joined] = translate_text(joined, src, dst)
        out.append([cache[joined]])
    return out
