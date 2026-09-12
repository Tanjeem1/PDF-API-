from django.urls import path

from editor.views import TranslatePDFView, WatermarkPDFView

# Spec paths have no trailing slash. Twins with a slash are registered so
# Postman cannot lose a multipart POST to a redirect.
urlpatterns = [
    path("api/translate-pdf", TranslatePDFView.as_view(), name="translate-pdf"),
    path("api/translate-pdf/", TranslatePDFView.as_view(), name="translate-pdf-slash"),
    path("editor/pdf/watermark", WatermarkPDFView.as_view(), name="watermark-pdf"),
    path("editor/pdf/watermark/", WatermarkPDFView.as_view(), name="watermark-pdf-slash"),
]
