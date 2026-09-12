import logging
import re
import time

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


def _mymemory_code(code: str) -> str:
    """Map ISO codes like 'en' / 'bn' to MyMemory locales (en-GB, bn-IN)."""
    global _MYMEMORY_CODES
    if _MYMEMORY_CODES is None:
        raw = MyMemoryTranslator(source="en-GB", target="bn-IN").get_supported_languages(as_dict=True)
        mapped: dict[str, str] = {}
        for locale in raw.values():
            locale = str(locale)
            short = locale.split("-", 1)[0].lower()
            mapped.setdefault(short, locale)
            mapped[locale.lower()] = locale
        # Prefer common locales when several exist.
        mapped["en"] = "en-GB"
        mapped["bn"] = "bn-IN"
        mapped["zh"] = "zh-CN"
        _MYMEMORY_CODES = mapped
    key = code.strip().lower()
    if key in _MYMEMORY_CODES:
        return _MYMEMORY_CODES[key]
    raise LanguageNotSupportedException(code)


def _is_unchanged(original: str, translated: str) -> bool:
    return (translated or "").strip().rstrip(".!?").lower() == (original or "").strip().rstrip(".!?").lower()


def _translate_with_google(text: str, source: str, target: str) -> str:
    return GoogleTranslator(source=source, target=target).translate(text)


def _translate_with_mymemory(text: str, source: str, target: str) -> str:
    src = _mymemory_code(source)
    dst = _mymemory_code(target)
    pieces = chunk_text(text, 450) or [text]
    translator = MyMemoryTranslator(source=src, target=dst)
    out = " ".join(translator.translate(piece) for piece in pieces)
    if _is_unchanged(text, out):
        raise RuntimeError("MyMemory returned the original text")
    return out


def _translate_with_lingva(text: str, source: str, target: str) -> str:
    import requests
    from requests.utils import quote

    src = normalize_language_code(source)
    dst = normalize_language_code(target)
    url = f"https://lingva.ml/api/v1/{src}/{dst}/{quote(text)}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    out = (response.json() or {}).get("translation") or ""
    if not out.strip() or _is_unchanged(text, out):
        raise RuntimeError("Lingva returned empty or original text")
    return out


def _google_translate(text: str, source: str, target: str) -> str:
    """Google, then MyMemory, then Lingva. Reject unchanged copy as a failure."""
    errors: list[Exception] = []
    for name, fn in (
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
        translated_page: list[str] = []
        for block in page:
            key = block
            if key not in cache:
                cache[key] = translate_text(block, src, dst)
            translated_page.append(cache[key])
        out.append(translated_page)
    return out
