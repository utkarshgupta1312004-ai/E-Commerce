# AI Assistant API Contract & UI Action Schema

## Endpoint

- **URL**: `/api/assistant/message/`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Rate Limit**: 20 requests / minute per client IP (HTTP 429 when exceeded)

### Request Payload

```json
{
  "message": "Compare the top headphones on my screen",
  "session_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a", // optional
  "browser_context": { // optional; extracted in real-time by widget
    "url": "/products/",
    "page_title": "Audio & Headphones | Cartivo",
    "cart_count": 2,
    "visible_products": [
      { "id": 1, "title": "Studio ANC Pro", "price": "299.00" },
      { "id": 2, "title": "Wireless Earbuds", "price": "49.00" }
    ]
  }
}
```

### Response Payload (HTTP 200)

```json
{
  "session_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a",
  "reply": "### ⚖️ Side-by-Side Comparison: Studio ANC Pro vs Wireless Earbuds...",
  "actions": [
    {
      "type": "compare_products",
      "payload": {
        "products": [ ... ],
        "verdict": { ... },
        "product_ids": [1, 2]
      }
    }
  ]
}
```

---

## Tool UI Actions Specification

Each tool executed during a conversation turn may emit a deterministic `ui_action` object. The frontend `ChatWidget` dispatcher consumes this list and triggers client-side interactions.

### 1. `compare_products`
Fired when products are compared side-by-side.
```json
{
  "type": "compare_products",
  "payload": {
    "products": [
      { "id": 1, "title": "Studio ANC Pro", "price": 299.0, "rating": 4.8 },
      { "id": 2, "title": "Wireless Earbuds", "price": 49.0, "rating": 4.3 }
    ],
    "verdict": {
      "best_value": "Wireless Earbuds",
      "highest_rated": "Studio ANC Pro",
      "summary": "Wireless Earbuds offers the best price at $49.00..."
    },
    "product_ids": [1, 2]
  }
}
```
*Frontend behavior*:
- Highlights the compared product cards in the DOM with glowing borders.
- Smoothly scrolls to the product grid section.

### 2. `filter_products`
Fired when products are searched or filtered.
```json
{
  "type": "filter_products",
  "payload": {
    "query": "headphones",
    "category": "electronics",
    "brand": "sony",
    "min_price": 20.0,
    "max_price": 150.0,
    "product_ids": [4, 7, 12],
    "count": 3
  }
}
```
*Frontend behavior*:
- Highlights or filters the product cards matching `product_ids` inside the product grid container (`.product-card[data-product-id]`).
- Smoothly scrolls the viewport to the product grid section.

### 2. `update_cart_badge`
Fired when an item is added to the cart via `add_to_cart`.
```json
{
  "type": "update_cart_badge",
  "payload": {
    "count": 3,
    "product_id": 12,
    "quantity": 1
  }
}
```
*Frontend behavior*:
- Updates the badge text inside `#cart-badge` (desktop header and mobile navigation).
- Triggers a subtle pulse/bounce animation on the cart icon to provide instant feedback.

### 3. `open_modal`
Fired when an explicit modal should be opened (e.g. coupon modal, cart modal, login modal).
```json
{
  "type": "open_modal",
  "payload": {
    "modal_id": "quick-view-modal"
  }
}
```
*Frontend behavior*:
- Calls `window.openModal(modal_id)` or removes `.hidden` / adds `.active` to the specified element.

### 4. `navigate_to`
Fired when the user requests navigation to a known storefront URL.
```json
{
  "type": "navigate_to",
  "payload": {
    "url": "/accounts/orders/",
    "new_tab": false
  }
}
```
*Frontend behavior*:
- Redirects browser location to `payload.url` (or opens new tab if `new_tab: true`).

### 5. `highlight_element`
Fired when the assistant wants to draw attention to a UI component.
```json
{
  "type": "highlight_element",
  "payload": {
    "selector": "#deals-banner"
  }
}
```
*Frontend behavior*:
- Selects the target element via `document.querySelector(selector)`.
- Scrolls element into view with smooth behavior.
- Applies a temporary pulsing glow ring for 3 seconds.
