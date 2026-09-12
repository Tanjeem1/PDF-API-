import logging

from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class TranslationServiceError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Translation service unavailable, try again"
    default_code = "translation_unavailable"


class BadPDFError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "File is not a valid PDF"
    default_code = "bad_pdf"


class FileTooLargeError(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "Uploaded file is too large."
    default_code = "file_too_large"


def _as_error(message, status_code):
    return Response({"error": str(message)}, status=status_code)


def custom_exception_handler(exc, context):
    """Normalize non-field errors to {"error": "..."} while keeping DRF field dicts."""
    if isinstance(exc, (RequestDataTooBig, TooManyFieldsSent)):
        return _as_error("Uploaded file is too large.", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    if isinstance(exc, TranslationServiceError):
        return _as_error(exc.detail, status.HTTP_502_BAD_GATEWAY)

    if isinstance(exc, FileTooLargeError):
        return _as_error(exc.detail, status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    if isinstance(exc, BadPDFError):
        return _as_error(exc.detail, status.HTTP_400_BAD_REQUEST)

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception")
        return _as_error("Internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)

    data = response.data
    if isinstance(data, dict):
        if set(data.keys()) <= {"detail", "code"}:
            return _as_error(data.get("detail", "Request failed"), response.status_code)
        return response
    if isinstance(data, list) and data:
        return _as_error(data[0], response.status_code)
    return _as_error(data, response.status_code)
