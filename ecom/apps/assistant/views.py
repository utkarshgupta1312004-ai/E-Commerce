"""
Cartivo AI Assistant - API Views

Endpoint: POST /api/assistant/message/
Provides rate-limited, context-aware, authenticated communication with
the Cartivo AI Shopping Concierge.
"""

import json
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.assistant.models import ChatSession, ChatMessage
from apps.assistant.gemini_client import GeminiAssistantClient
from apps.assistant.action_validator import ActionValidator
from apps.audit.services import AuditService

logger = logging.getLogger(__name__)

RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 60


def check_rate_limit(client_ip: str) -> bool:
    """
    Checks if a client IP has exceeded the rate limit.
    Returns True if allowed, False if exceeded.
    """
    if not client_ip:
        return True
    cache_key = f"assistant_rate_limit_{client_ip}"
    request_count = cache.get(cache_key, 0)
    if request_count >= RATE_LIMIT_REQUESTS:
        return False

    if request_count == 0:
        cache.set(cache_key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
    else:
        try:
            cache.incr(cache_key)
        except Exception:
            cache.set(cache_key, request_count + 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
    return True


@method_decorator(csrf_exempt, name='dispatch')
class AssistantMessageView(View):
    """
    API View to handle incoming user messages for the AI Assistant.
    Endpoint: POST /api/assistant/message/
    Payload: { "message": "...", "session_id": "optional-uuid", "browser_context": {...} }
    Response: { "session_id": "uuid", "reply": "...", "actions": [...] }
    """

    def post(self, request, *args, **kwargs):
        client_ip = AuditService.get_client_ip(request)
        if not check_rate_limit(client_ip):
            return JsonResponse(
                {"error": "Too many requests. Please slow down and wait a minute before messaging again."},
                status=429
            )

        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            return JsonResponse({"error": "Invalid JSON request body."}, status=400)

        raw_message = body.get('message', '').strip()
        if not raw_message:
            return JsonResponse({"error": "Message content cannot be empty."}, status=400)

        try:
            # 1. Resolve or create ChatSession
            session_id = body.get('session_id')
            session = None
            if session_id:
                try:
                    session = ChatSession.objects.filter(session_id=session_id).first()
                except Exception:
                    session = None

            user = request.user if request.user and request.user.is_authenticated else None
            if not session:
                session = ChatSession.objects.create(user=user)
            elif user and not session.user:
                session.user = user
                session.save(update_fields=['user'])

            # 2. Persist user message
            ChatMessage.objects.create(
                session=session,
                sender='user',
                text=raw_message
            )

            # 3. Retrieve conversation history for context (last 10 turns)
            history_records = session.messages.order_by('timestamp')[:10]
            history = [{'sender': msg.sender, 'text': msg.text} for msg in history_records]

            # 4. Audit callback for sensitive backend tools
            def audit_callback(tool_name: str, args: dict, result: dict):
                SENSITIVE_TOOLS = {'apply_coupon', 'add_to_cart', 'track_order'}
                if tool_name not in SENSITIVE_TOOLS:
                    return

                status_desc = "failed" if result.get("error") else "success"
                details = f"Tool: {tool_name} | Args: {args} | Result Status: {status_desc}"
                AuditService.log(
                    action=f"assistant_tool_{tool_name}",
                    request=request,
                    user=user,
                    department="assistant",
                    details=details
                )

            browser_context = body.get('browser_context', {})
            if browser_context and isinstance(browser_context, dict) and 'url' in browser_context:
                session.metadata['last_url'] = browser_context.get('url')
                session.metadata['last_page_title'] = browser_context.get('page_title')
                session.save(update_fields=['metadata'])

            # 5. Execute turn via Gemini client
            client = GeminiAssistantClient()
            reply, raw_tool_calls, raw_tool_results, ui_actions = client.send_message(
                message=raw_message,
                history=history,
                request=request,
                browser_context=browser_context,
                audit_callback=audit_callback
            )

            # 6. Server-side validation of UI actions
            validated_actions = ActionValidator.validate_actions(ui_actions)

            # 7. Persist assistant message
            ChatMessage.objects.create(
                session=session,
                sender='assistant',
                text=reply,
                raw_tool_calls=raw_tool_calls,
                raw_tool_results=raw_tool_results,
                actions=validated_actions
            )

            return JsonResponse({
                "session_id": str(session.session_id),
                "reply": reply,
                "actions": validated_actions
            }, status=200)

        except Exception as e:
            logger.exception(f"Unhandled error in AssistantMessageView: {e}")
            # Never expose internal exceptions, tracebacks, or operational errors to customers
            return JsonResponse({
                "session_id": str(session.session_id) if session else "",
                "reply": "Sorry, I'm having trouble accessing that information right now. Please try again in a moment.",
                "actions": []
            }, status=200)
