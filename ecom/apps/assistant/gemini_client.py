import logging
import os
import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.conf import settings
from apps.assistant.tools import registry, ToolRegistry

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """
You are the Cartivo AI Shopping Assistant, an expert e-commerce concierge with real-time browser awareness.
Your capabilities:
1. Real-time Browser Awareness: You receive real-time data from the shopper's browser (current page URL, page title, visible products rendered on screen, active bag item count).
2. Product Features & Deep Specs: Extract and explain technical specifications, materials, warranty, ratings, and features of products (`get_product_features`).
3. Side-by-Side Comparison: Compare products side-by-side on price, specs, rating, pros, and cons (`compare_products`).
4. Discover & Assist: Help users discover products, filter catalog (`filter_products`), add items to cart (`add_to_cart`), check coupons (`apply_coupon`), track orders (`track_order`), and navigate (`navigate_to`, `highlight_element`).
5. Answer clearly, accurately, and proactively guide user shopping decisions with direct insights.
"""

class GeminiAssistantClient:
    """
    Client for interacting with Google Gemini models using the modern `google-genai` SDK.
    Employs manual function calling loops to enable fine-grained validation,
    deterministic UI action dispatch, and audit logging.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
        self.model_name = model or getattr(settings, 'GEMINI_MODEL', 'gemini-3.6-flash') or os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')
        self.registry: ToolRegistry = registry
        self._genai_client = None

        if self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai Client: {e}")
                self._genai_client = None

    def _build_sdk_tools(self):
        """
        Builds Google GenAI Tool specifications using parameters_json_schema.
        """
        from google.genai import types

        declarations = []
        for tool in self.registry.all_tools():
            declarations.append(types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.parameters,
            ))
        return [types.Tool(function_declarations=declarations)]

    def send_message(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        request=None,
        browser_context: Optional[Dict[str, Any]] = None,
        audit_callback: Optional[Callable[[str, Dict[str, Any], Dict[str, Any]], None]] = None,
        max_iterations: int = 5,
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Runs the conversational turn.
        Returns:
            reply: str - The final assistant response text.
            raw_tool_calls: list of tool calls made during the turn.
            raw_tool_results: list of results returned from tool executions.
            ui_actions: list of UI action payloads meant for frontend dispatcher.
        """
        if not self._genai_client or not self.api_key:
            logger.info("Gemini API key not configured or client unavailable. Using deterministic local fallback.")
            return self._fallback_response(message, request=request, browser_context=browser_context, audit_callback=audit_callback)

        try:
            from google.genai import types

            sdk_tools = self._build_sdk_tools()
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=sdk_tools,
                temperature=0.3,
            )

            contents: List[types.Content] = []

            # Populate historical context (up to last 10 messages)
            if history:
                for item in history[-10:]:
                    role = 'user' if item.get('sender') == 'user' else 'model'
                    contents.append(types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=item.get('text', ''))]
                    ))

            # Build enriched prompt with browser context if provided
            context_header = ""
            if browser_context:
                url = browser_context.get("url", "")
                page_title = browser_context.get("page_title", "")
                vis = browser_context.get("visible_products", [])
                cart_c = browser_context.get("cart_count", 0)
                prod_strs = [f"#{p.get('id')}: {p.get('title')} (₹{p.get('price')})" for p in vis[:8]]
                context_header = (
                    f"[Browser Context: Viewing '{page_title}' ({url}) | "
                    f"Visible Products: {', '.join(prod_strs) or 'None on screen'} | "
                    f"Bag Items: {cart_c}]\n"
                )

            effective_prompt = f"{context_header}{message}" if context_header else message

            # Add current user prompt
            contents.append(types.Content(
                role='user',
                parts=[types.Part.from_text(text=effective_prompt)]
            ))

            raw_tool_calls: List[Dict[str, Any]] = []
            raw_tool_results: List[Dict[str, Any]] = []
            ui_actions: List[Dict[str, Any]] = []

            for iteration in range(max_iterations):
                response = self._genai_client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                function_calls = getattr(response, 'function_calls', None)
                if not function_calls:
                    # Model produced final text without calling more tools
                    reply = response.text or "I am ready to help you find products or assist with your shopping!"
                    return reply, raw_tool_calls, raw_tool_results, ui_actions

                # Append model's candidate turn containing function calls
                if response.candidates and response.candidates[0].content:
                    contents.append(response.candidates[0].content)

                # Process all requested function calls manually
                tool_response_parts = []
                for call in function_calls:
                    fn_name = call.name
                    fn_args = dict(call.args) if hasattr(call, 'args') and call.args else {}

                    raw_tool_calls.append({"name": fn_name, "args": fn_args})

                    # Execute tool via registry
                    result = self.registry.execute(fn_name, fn_args, request=request)
                    raw_tool_results.append({"name": fn_name, "result": result})

                    # Collect UI action if returned
                    if result.get("ui_action"):
                        ui_actions.append(result["ui_action"])

                    # Trigger audit logging callback for backend mutations/queries
                    if audit_callback:
                        try:
                            audit_callback(fn_name, fn_args, result)
                        except Exception as e:
                            logger.error(f"Audit callback error for {fn_name}: {e}")

                    # Prepare function response part for Gemini
                    tool_response_parts.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": result}
                        )
                    )

                # Append tool responses to content history for the next iteration
                contents.append(types.Content(
                    role='user',
                    parts=tool_response_parts
                ))

            # If reached max_iterations, return whatever output or fallback
            return "I have processed your requests. Is there anything else you'd like to check?", raw_tool_calls, raw_tool_results, ui_actions

        except Exception as e:
            logger.exception(f"Error during Gemini API call: {e}. Falling back to deterministic handler.")
            return self._fallback_response(message, request=request, audit_callback=audit_callback)

    def _fallback_response(
        self,
        message: str,
        request=None,
        browser_context: Optional[Dict[str, Any]] = None,
        audit_callback: Optional[Callable[[str, Dict[str, Any], Dict[str, Any]], None]] = None
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Deterministic, local rule-based response generator when Gemini API is unavailable or unconfigured.
        Guarantees that the assistant can still search products, filter, compare, extract features, apply coupons, and track orders.
        """
        text = message.strip()
        lower = text.lower()
        raw_tool_calls: List[Dict[str, Any]] = []
        raw_tool_results: List[Dict[str, Any]] = []
        ui_actions: List[Dict[str, Any]] = []

        def run_tool(name: str, args: Dict[str, Any]):
            raw_tool_calls.append({"name": name, "args": args})
            res = self.registry.execute(name, args, request=request)
            raw_tool_results.append({"name": name, "result": res})
            if res.get("ui_action"):
                ui_actions.append(res["ui_action"])
            if audit_callback:
                try:
                    audit_callback(name, args, res)
                except Exception as ex:
                    logger.error(f"Fallback audit callback error: {ex}")
            return res

        # 0. Product Comparison (compare, vs, versus, difference)
        if "compare" in lower or " vs " in lower or "versus" in lower or "difference between" in lower:
            cleaned = text.replace("compare", "").replace("difference between", "").replace("and", " ").replace("vs", " ").replace("versus", " ")
            parts = [p.strip() for p in cleaned.split() if len(p.strip()) > 3]
            candidates = parts[:2]
            if not candidates and browser_context:
                vis = browser_context.get("visible_products", [])
                if len(vis) >= 2:
                    candidates = [vis[0].get("title", ""), vis[1].get("title", "")]

            comp_res = run_tool("compare_products", {"products": candidates})
            if comp_res.get("success") and comp_res.get("products"):
                prods = comp_res["products"]
                verdict = comp_res.get("verdict", {}).get("summary", "")
                p1 = prods[0]
                p2 = prods[1] if len(prods) > 1 else prods[0]
                reply = (
                    f"### ⚖️ Side-by-Side Comparison: **{p1['title']}** vs **{p2['title']}**\n\n"
                    f"- **Price**: ₹{p1['price']:.2f} vs ₹{p2['price']:.2f}\n"
                    f"- **Rating**: {p1['rating']}★ ({p1['review_count']} reviews) vs {p2['rating']}★ ({p2['review_count']} reviews)\n"
                    f"- **Brand & Category**: {p1['brand']} ({p1['category']}) vs {p2['brand']} ({p2['category']})\n"
                    f"- **Highlight**: {p1['badge'] or 'Original'} vs {p2['badge'] or 'Original'}\n\n"
                    f"💡 **Verdict**: {verdict}\n\n"
                    f"I've highlighted these items in your catalog view!"
                )
            else:
                reply = comp_res.get("error", "I couldn't identify enough products to compare. Please specify two products.")
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 0.1 Product Features & Deep Specifications
        if "feature" in lower or "spec" in lower or "tell me about" in lower or "details of" in lower:
            target_prod = ""
            for trigger in ["features of", "specs of", "specifications of", "tell me about", "details of", "features", "specs"]:
                if trigger in lower:
                    target_prod = lower.split(trigger)[-1].strip()
                    break
            if not target_prod and browser_context:
                vis = browser_context.get("visible_products", [])
                if vis:
                    target_prod = vis[0].get("title", "")

            feat_res = run_tool("get_product_features", {"product": target_prod})
            if feat_res.get("success") and feat_res.get("product"):
                prod = feat_res["product"]
                bullet_list = "\n".join([f"- {f}" for f in prod.get("features", [])])
                reply = (
                    f"### 🔍 Detailed Product Features: **{prod['title']}**\n\n"
                    f"{prod.get('description', '')}\n\n"
                    f"**Core Specifications:**\n"
                    f"{bullet_list}\n\n"
                    f"Would you like to add **{prod['title']}** to your bag or compare it with another model?"
                )
            else:
                reply = feat_res.get("error", "Could not locate the requested product specifications.")
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 0.2 Real-time Browser View / On Screen Products
        if ("screen" in lower or "visible" in lower or "page" in lower) and browser_context and browser_context.get("visible_products"):
            vis = browser_context["visible_products"]
            items_list = "\n".join([f"- **{p.get('title')}**: ₹{p.get('price')}" for p in vis[:6]])
            reply = (
                f"Browsing **{browser_context.get('page_title', 'Cartivo')}** (`{browser_context.get('url', '/')}`).\n\n"
                f"Products currently visible on your screen:\n"
                f"{items_list}\n\n"
                f"Ask me to **compare** any of these or check their **detailed specifications**!"
            )
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 1. Coupon queries
        if "coupon" in lower or "promo" in lower or "discount" in lower and any(w in lower for w in ["apply", "code", "SAVE", "WELCOME"]):
            words = text.replace(",", " ").replace(".", " ").split()
            code = "SAVE10"
            for w in words:
                if w.isupper() and len(w) >= 4:
                    code = w
                    break
            res = run_tool("apply_coupon", {"code": code})
            reply = res.get("message", f"Processed coupon code {code}.")
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 2. Add to cart
        if "add" in lower and "cart" in lower:
            # Try to find a product mentioned
            product_query = lower.replace("add", "").replace("to", "").replace("cart", "").replace("the", "").replace("please", "").strip()
            if not product_query:
                product_query = "product"
            
            search_res = run_tool("search_products", {"query": product_query, "limit": 1})
            products = search_res.get("products", [])
            if products:
                prod = products[0]
                cart_res = run_tool("add_to_cart", {"product_id": prod["id"], "quantity": 1})
                reply = f"Added '{prod['name']}' to your cart! You now have {cart_res.get('cart_count', 1)} item(s) in your cart."
            else:
                reply = "I couldn't identify the specific product you want to add to your cart. Please try specifying the product name."
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 3. Order tracking
        if "track" in lower or ("order" in lower and any(char.isdigit() for char in text)):
            import re
            match = re.search(r'#?([A-Za-z0-9\-]{5,})', text)
            order_id = match.group(1) if match else "ORD-1001"
            res = run_tool("track_order", {"order_id": order_id})
            reply = f"Order #{res.get('order_id')}: Status is **{res.get('status')}**. Estimated delivery: {res.get('estimated_delivery')}."
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 4. Filter products (under $X, cheap, category)
        if "under" in lower or "below" in lower or "less than" in lower or "filter" in lower or "cheap" in lower:
            import re
            price_match = re.search(r'[\$₹]?(\d+)', text)
            max_p = float(price_match.group(1)) if price_match else None
            filter_args = {}
            if max_p is not None:
                filter_args["max_price"] = max_p
            
            res = run_tool("filter_products", filter_args)
            count = res.get("count", 0)
            if count > 0:
                reply = f"I've filtered the catalog for you. Found {count} product(s) matching your criteria."
            else:
                reply = "I couldn't find any products matching those specific price/filter criteria."
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 5. Product search (default query)
        clean_query = lower.replace("find", "").replace("search", "").replace("show", "").replace("for", "").replace("me", "").strip()
        if clean_query and len(clean_query) > 1:
            res = run_tool("search_products", {"query": clean_query, "limit": 6})
            prods = res.get("products", [])
            count = res.get("count", 0)
            if count > 0:
                names = ", ".join(p["name"] for p in prods[:3])
                reply = f"Found {count} item(s) for '{clean_query}', such as: {names}. The catalog view has been updated for you!"
            else:
                reply = f"I searched for '{clean_query}' but didn't find exact matches. Try browsing our popular categories or adjusting your terms."
            return reply, raw_tool_calls, raw_tool_results, ui_actions

        # 6. General greeting / guidance
        reply = (
            "Hello! I am your Cartivo AI Shopping Assistant. I can help you:\n"
            "- **Search products**: 'Show me wireless headphones' or 'Find running shoes'\n"
            "- **Filter by price**: 'Show items under ₹500'\n"
            "- **Manage cart**: 'Add shoes to cart'\n"
            "- **Check coupons**: 'Apply coupon SAVE10'\n"
            "- **Track orders**: 'Track order ORD-1001'\n\n"
            "How can I help you today?"
        )
        return reply, raw_tool_calls, raw_tool_results, ui_actions
