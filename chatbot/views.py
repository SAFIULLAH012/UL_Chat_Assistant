import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .services.pipeline import process_message

logger = logging.getLogger("chatbot")


@csrf_exempt
@require_http_methods(["POST"])
def chat(request):
    """
    POST /api/chat/
    Body: {"message": "bscs ki fees kitni hai"}
    Response: {
        "reply": "...",
        "intent": "fee",
        "intent_confidence": 0.81,
        "entities": [{"entity_type": "program", "id": "bs_computer_science", "canonical": "BS Computer Science", "matched_text": "bscs"}],
        "matched_chunk_id": "program_bs_computer_science",
        "match_quality": 0.91,
        "answer_verified": true
    }

    NOTE on CSRF/CORS: csrf_exempt is used here because this is a stateless
    JSON API likely called from a separate frontend origin. Before going to
    production, put this behind proper auth/rate-limiting and configure
    django-cors-headers with your frontend's real origin instead of "*".
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "'message' is required"}, status=400)
    if len(message) > 1000:
        return JsonResponse({"error": "message too long"}, status=400)

    try:
        result = process_message(message)
    except Exception:
        logger.exception("chatbot pipeline failed for message=%r", message)
        return JsonResponse({"error": "internal error, please try again"}, status=500)

    return JsonResponse(result)


@require_http_methods(["GET"])
def health(request):
    return JsonResponse({"status": "ok"})
