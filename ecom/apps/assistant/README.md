# Cartivo AI Shopping Assistant (`apps.assistant`)

The AI Shopping Assistant enables conversational e-commerce with real-time UI manipulation powered by Google Gemini and a deterministic tool execution registry.

## Key Features

1. **Deterministic Function Calling & Safety**:
   - Uses the modern `google-genai` Python SDK with manual function-calling loops.
   - Every tool call is intercepted, validated, executed against application models or session state, and logged.
   - Zero automatic unmonitored SDK function executions.

2. **UI Action Dispatcher**:
   - Backend tools and UI tools return a structured `ui_action` payload.
   - Frontend floating chat widget (`chat-widget.js`) dispatches DOM operations (filter products, bounce cart badge, open modal, highlight element, navigate).

3. **Audit Logging & Security**:
   - Backend tool invocations (mutations, coupon applications, cart changes) trigger `AuditService.log` under the `'assistant'` department.
   - Rate limited to 20 requests per minute per client IP.
   - Sensitive environment variables (`GEMINI_API_KEY`, `GEMINI_MODEL`) are read strictly from environment configurations.

4. **Resilient Local Fallback**:
   - If `GEMINI_API_KEY` is unset or network calls fail, the assistant gracefully falls back to local query handling, allowing testing and development without requiring an API key.

## Tool Registry

| Tool Name | Kind | Description | UI Action |
|-----------|------|-------------|-----------|
| `compare_products` | Backend | Compare products side-by-side on specs, price & rating | `compare_products` |
| `get_product_features` | Backend | Extract deep product specs, materials & highlights | `highlight_element` |
| `search_products` | Backend | Search catalog by query keyword | `filter_products` |
| `filter_products` | Backend | Filter catalog by price range, brand, category | `filter_products` |
| `add_to_cart` | Backend | Add item to customer session cart | `update_cart_badge` |
| `apply_coupon` | Backend | Validate and apply promotion code | None |
| `track_order` | Backend | Check fulfillment status of an order | None |
| `navigate_to` | UI | Redirect customer to page | `navigate_to` |
| `highlight_element` | UI | Scroll to & glow-highlight element | `highlight_element` |
| `open_modal` | UI | Open modal dialog | `open_modal` |

## Frontend Integration

The widget is provided via:
```django
{% include "assistant/widget.html" %}
```
Included right before the closing `</body>` tag in `templates/base.html`.
