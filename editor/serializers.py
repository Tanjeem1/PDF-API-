from deep_translator.exceptions import LanguageNotSupportedException
from rest_framework import serializers

from editor.services.translator import normalize_language_code
from editor.validators import normalize_hex_color, validate_uploaded_pdf

POSITION_CHOICES = [
    "top-left",
    "top-center",
    "top-right",
    "center",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]


class TranslateRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    source_language = serializers.CharField(max_length=40)
    target_language = serializers.CharField(max_length=40)

    def validate_file(self, uploaded):
        validate_uploaded_pdf(uploaded)
        return uploaded

    def validate_source_language(self, value):
        return self._clean_language(value)

    def validate_target_language(self, value):
        return self._clean_language(value)

    @staticmethod
    def _clean_language(value: str) -> str:
        try:
            return normalize_language_code(value)
        except (LanguageNotSupportedException, Exception):
            raise serializers.ValidationError(f"Unsupported language code: {value}")


class WatermarkRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    text = serializers.CharField(max_length=200, allow_blank=False, trim_whitespace=True)
    position = serializers.ChoiceField(choices=POSITION_CHOICES)
    opacity = serializers.FloatField(min_value=0.0, max_value=1.0)
    color = serializers.CharField(max_length=7)

    def validate_file(self, uploaded):
        validate_uploaded_pdf(uploaded)
        return uploaded

    def validate_color(self, value):
        return normalize_hex_color(value)
