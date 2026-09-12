from django.core.exceptions import RequestDataTooBig, TooManyFieldsSent
from django.http import JsonResponse


class RequestSizeLimitMiddleware:
    """Map Django parse-time size errors to JSON 413 (DRF never sees these)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except RequestDataTooBig:
            return JsonResponse({"error": "Uploaded file is too large."}, status=413)
        except TooManyFieldsSent:
            return JsonResponse({"error": "Uploaded file is too large."}, status=413)
