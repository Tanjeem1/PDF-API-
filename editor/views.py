import logging
from io import BytesIO

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from editor.exceptions import BadPDFError, TranslationServiceError
from editor.serializers import TranslateRequestSerializer, WatermarkRequestSerializer
from editor.services.pdf_builder import build_translated_pdf
from editor.services.pdf_extract import extract_pages, has_extractable_text
from editor.services.pdf_watermark import apply_watermark
from editor.services.translator import translate_pages

logger = logging.getLogger(__name__)


def _pdf_response(payload: bytes, filename: str) -> FileResponse:
    buffer = BytesIO(payload)
    buffer.seek(0)
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )


class TranslatePDFView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        logger.info("translate-pdf request received")
        serializer = TranslateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data["file"]
        source = serializer.validated_data["source_language"]
        target = serializer.validated_data["target_language"]
        pdf_bytes = uploaded.read()
        uploaded.seek(0)

        try:
            pages, sizes = extract_pages(pdf_bytes)
        except BadPDFError:
            raise
        except Exception:
            logger.exception("Failed to extract PDF text")
            raise BadPDFError("File is not a valid PDF")

        if not has_extractable_text(pages):
            return Response(
                {
                    "error": (
                        "No extractable text found. "
                        "Scanned or image-only PDFs are not supported."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(pages) > settings.MAX_TRANSLATE_PAGES:
            return Response(
                {
                    "error": (
                        f"This PDF has {len(pages)} pages. "
                        f"The public translate API accepts at most "
                        f"{settings.MAX_TRANSLATE_PAGES} pages. "
                        "Use a PDF with 50 pages or fewer."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            translated = translate_pages(pages, source, target)
            output = build_translated_pdf(translated, sizes)
        except TranslationServiceError:
            raise
        except Exception:
            logger.exception("Failed to build translated PDF")
            return Response(
                {"error": "Failed to generate translated PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("translate-pdf completed (%s pages)", len(translated))
        return _pdf_response(output, "translated.pdf")


class WatermarkPDFView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        logger.info("watermark request received")
        serializer = WatermarkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded = serializer.validated_data["file"]
        pdf_bytes = uploaded.read()
        uploaded.seek(0)

        try:
            output = apply_watermark(
                pdf_bytes,
                text=serializer.validated_data["text"],
                position=serializer.validated_data["position"],
                opacity=serializer.validated_data["opacity"],
                color=serializer.validated_data["color"],
            )
        except BadPDFError:
            raise
        except Exception:
            logger.exception("Failed to watermark PDF")
            return Response(
                {"error": "Failed to watermark PDF"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("watermark completed")
        return _pdf_response(output, "watermarked.pdf")
