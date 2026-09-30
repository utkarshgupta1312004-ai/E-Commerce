"""
Cartivo AI Assistant - Action Validator

Strict server-side validation for all assistant UI actions before they
are dispatched to the frontend ChatWidget. Enforces strict schema,
whitelisted action types, safe relative routes, safe modal IDs,
and safe CSS selectors.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from apps.assistant.knowledge import is_permitted_route

logger = logging.getLogger(__name__)

ALLOWED_ACTIONS = {
    "compare_products",
    "filter_products",
    "update_cart_badge",
    "open_modal",
    "navigate_to",
    "highlight_element",
}

ALLOWED_MODAL_IDS = {
    "order-tracking-modal",
    "quick-view-modal",
    "coupon-modal",
    "cart-modal",
    "login-modal",
    "address-modal",
    "add-to-cart-confirm-modal",
}

# Safe CSS selector regex: allows #id, .class, tag, [data-attr="val"]
SAFE_SELECTOR_REGEX = re.compile(r'^[#\.\w\-\s,>+~:\[\]="\'*]+$')


class ActionValidationError(Exception):
    """Raised when a UI action fails security or schema validation."""
    pass


class ActionValidator:
    """
    Validates and sanitizes UI actions emitted by the AI assistant or tool handlers.
    """

    @classmethod
    def validate_action(cls, action: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validates a single UI action dictionary.
        Returns:
            (is_valid: bool, sanitized_action: Optional[dict], error_message: Optional[str])
        """
        if not isinstance(action, dict):
            return False, None, "Action must be a dictionary."

        action_type = action.get("type")
        if not action_type or not isinstance(action_type, str):
            return False, None, "Action must have a string 'type'."

        if action_type not in ALLOWED_ACTIONS:
            return False, None, f"Action type '{action_type}' is not allowed."

        payload = action.get("payload")
        if payload is None or not isinstance(payload, dict):
            payload = {}

        sanitized_payload: Dict[str, Any] = {}

        # 1. navigate_to validation
        if action_type == "navigate_to":
            url = payload.get("url")
            if not url or not isinstance(url, str):
                return False, None, "navigate_to requires a non-empty string 'url'."
            url = url.strip()
            if not is_permitted_route(url):
                return False, None, f"URL '{url}' is not a permitted internal Cartivo route."
            sanitized_payload["url"] = url
            sanitized_payload["new_tab"] = bool(payload.get("new_tab", False))

        # 2. open_modal validation
        elif action_type == "open_modal":
            modal_id = payload.get("modal_id")
            if not modal_id or not isinstance(modal_id, str):
                return False, None, "open_modal requires a non-empty string 'modal_id'."
            modal_id = modal_id.strip()
            if modal_id not in ALLOWED_MODAL_IDS:
                return False, None, f"modal_id '{modal_id}' is not in the allowed modal registry."
            sanitized_payload["modal_id"] = modal_id
            # Forward additional metadata if present
            for k in ["order_id", "status", "carrier", "estimated_delivery"]:
                if k in payload:
                    sanitized_payload[k] = str(payload[k])

        # 3. highlight_element validation
        elif action_type == "highlight_element":
            selector = payload.get("selector")
            if not selector or not isinstance(selector, str):
                return False, None, "highlight_element requires a non-empty string 'selector'."
            selector = selector.strip()
            if len(selector) > 200 or not SAFE_SELECTOR_REGEX.match(selector):
                return False, None, f"Selector '{selector}' contains unsafe characters."
            sanitized_payload["selector"] = selector

        # 4. update_cart_badge validation
        elif action_type == "update_cart_badge":
            count = payload.get("count", 0)
            try:
                count = int(count)
                if count < 0:
                    count = 0
            except (ValueError, TypeError):
                count = 0
            sanitized_payload["count"] = count
            if "product_id" in payload:
                try:
                    sanitized_payload["product_id"] = int(payload["product_id"])
                except (ValueError, TypeError):
                    pass
            if "product_title" in payload:
                sanitized_payload["product_title"] = str(payload["product_title"])[:150]
            if "message" in payload:
                sanitized_payload["message"] = str(payload["message"])[:200]

        # 5. filter_products validation
        elif action_type == "filter_products":
            sanitized_payload["query"] = str(payload.get("query", ""))[:100]
            sanitized_payload["count"] = int(payload.get("count", 0)) if isinstance(payload.get("count"), int) else 0

            # Validate product_ids if provided
            raw_pids = payload.get("product_ids", [])
            valid_pids = []
            if isinstance(raw_pids, list):
                for pid in raw_pids:
                    try:
                        valid_pids.append(int(pid))
                    except (ValueError, TypeError):
                        pass
            sanitized_payload["product_ids"] = valid_pids[:30]

            # Forward sanitized product objects if provided
            raw_products = payload.get("products", [])
            valid_products = []
            if isinstance(raw_products, list):
                for p in raw_products[:12]:
                    if isinstance(p, dict) and "id" in p and "title" in p:
                        valid_products.append({
                            "id": int(p.get("id", 0)),
                            "title": str(p.get("title", ""))[:120],
                            "price": float(p.get("price", 0.0)),
                            "rating": float(p.get("rating", 5.0)),
                            "image_url": str(p.get("image_url", "")),
                            "url": str(p.get("url", "/products/")),
                        })
            sanitized_payload["products"] = valid_products

        # 6. compare_products validation
        elif action_type == "compare_products":
            raw_pids = payload.get("product_ids", [])
            valid_pids = []
            if isinstance(raw_pids, list):
                for pid in raw_pids:
                    try:
                        valid_pids.append(int(pid))
                    except (ValueError, TypeError):
                        pass
            sanitized_payload["product_ids"] = valid_pids[:4]

            raw_prods = payload.get("products", [])
            valid_prods = []
            if isinstance(raw_prods, list):
                for p in raw_prods[:4]:
                    if isinstance(p, dict) and "title" in p:
                        valid_prods.append({
                            "id": int(p.get("id", 0)),
                            "title": str(p.get("title", ""))[:120],
                            "price": float(p.get("price", 0.0)),
                            "rating": float(p.get("rating", 5.0)),
                            "brand": str(p.get("brand", ""))[:60],
                            "category": str(p.get("category", ""))[:60],
                            "image_url": str(p.get("image_url", "")),
                            "url": str(p.get("url", "/products/")),
                        })
            sanitized_payload["products"] = valid_prods

            verdict = payload.get("verdict", {})
            if isinstance(verdict, dict):
                sanitized_payload["verdict"] = {
                    "best_value": str(verdict.get("best_value", ""))[:100],
                    "highest_rated": str(verdict.get("highest_rated", ""))[:100],
                    "summary": str(verdict.get("summary", ""))[:300],
                }

        sanitized_action = {
            "type": action_type,
            "payload": sanitized_payload,
        }
        return True, sanitized_action, None

    @classmethod
    def validate_actions(cls, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validates an array of action dictionaries, dropping invalid ones safely.
        """
        if not isinstance(actions, list):
            return []

        validated = []
        for act in actions:
            is_valid, sanitized, err = cls.validate_action(act)
            if is_valid and sanitized:
                validated.append(sanitized)
            else:
                logger.warning(f"Rejected invalid assistant UI action: {err} | Raw: {act}")
        return validated
