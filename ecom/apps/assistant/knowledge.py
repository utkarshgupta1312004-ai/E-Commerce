"""
Cartivo AI Assistant - Controlled Knowledge Layer

Contains authoritative static store information, policies, FAQs,
and permitted storefront navigation routes.
Dynamic information (products, stock, orders) is queried directly
from authoritative Django database models.
"""

# ==============================================================================
# 1. PERMITTED INTERNAL ROUTES (WHITELIST)
# ==============================================================================

PERMITTED_INTERNAL_ROUTES = {
    "/": "Home Storefront",
    "/products/": "Product Catalog & Collections",
    "/cart/": "Shopping Bag & Cart",
    "/wishlist/": "Saved Items & Wishlist",
    "/checkout/": "Checkout & Order Review",
    "/orders/": "Customer Order History & Tracking",
    "/accounts/profile/": "Customer Profile & Addresses",
    "/accounts/login/": "Customer Login",
    "/accounts/register/": "Customer Registration",
    "/accounts/settings/": "Account Settings",
    "/accounts/password/change/": "Change Password",
}


def is_permitted_route(url: str) -> bool:
    """
    Checks if a URL is a valid internal storefront route.
    Rejects any external URL, protocol, or unapproved endpoint.
    """
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    # Must start with forward slash, must not contain protocol or javascript
    if not url.startswith("/") or url.startswith("//") or ":" in url:
        return False

    # Exact match in whitelist
    if url in PERMITTED_INTERNAL_ROUTES:
        return True

    # Parameterized storefront routes
    if url.startswith("/products/") and len(url) > len("/products/"):
        return True
    if url.startswith("/category/") and len(url) > len("/category/"):
        return True
    if url.startswith("/orders/") and len(url) > len("/orders/"):
        return True

    return False


# ==============================================================================
# 2. STATIC STORE POLICIES (AUTHORITATIVE)
# ==============================================================================

STORE_POLICIES = {
    "shipping": {
        "title": "Shipping & Delivery Policy",
        "summary": (
            "Cartivo delivers across India via express logistics partners including "
            "Cartivo Express, BlueDart, and Delhivery. Standard delivery takes 2 to 4 business days. "
            "Free standard shipping is provided on all orders above ₹999 or with promo code 'FREESHIP'. "
            "For orders below ₹999, a flat shipping fee of ₹49 applies. Real-time courier tracking is provided for every order."
        ),
        "free_shipping_threshold": 999.0,
        "delivery_sla": "2-4 business days",
        "partners": ["Cartivo Express Logistics", "BlueDart Express", "Delhivery"],
    },
    "return": {
        "title": "Return Policy",
        "summary": (
            "Cartivo offers a 7-day hassle-free return window from the date of delivery. "
            "Eligible products must be unused, unwashed, and in their original packaging with tags intact. "
            "Free doorstep return pickup is scheduled once a return request is submitted through your account orders page."
        ),
        "return_window_days": 7,
        "pickup_type": "Free Doorstep Reverse Pickup",
        "eligibility": "Unused, unwashed, with original tags and brand box intact.",
    },
    "refund": {
        "title": "Refund Policy",
        "summary": (
            "Refunds are processed within 24 to 48 hours following quality inspection of returned goods. "
            "For prepaid orders (UPI, Cards, Net Banking), refunds are credited to the original payment source within 3 to 5 business days. "
            "For Cash on Delivery (COD) orders, refunds are credited directly to your bank account or UPI ID provided during return creation."
        ),
        "processing_time": "24-48 hours after warehouse receipt",
        "credit_timeline": "3-5 business days to original payment method",
    },
    "payment_methods": {
        "title": "Payment Methods & COD",
        "summary": (
            "Cartivo supports multiple secure payment options:\n"
            "1. Cash on Delivery (COD): Available for all serviceable pin codes across India.\n"
            "2. UPI: Google Pay, PhonePe, Paytm, and BHIM.\n"
            "3. Cards: Credit and Debit cards (Visa, MasterCard, RuPay, American Express) with 256-bit SSL encryption.\n"
            "4. Net Banking: All major Indian banks supported.\n"
            "All online transactions are 100% PCI-DSS compliant and secured with OTP two-factor authentication."
        ),
        "supports_cod": True,
        "supports_upi": True,
        "supports_cards": True,
    },
    "cancellation": {
        "title": "Order Cancellation Policy",
        "summary": (
            "You can cancel your order directly from your Orders page (/orders/) while the order status is 'Confirmed' or 'Preparing'. "
            "Once an order is packed or shipped, it cannot be cancelled directly; you can simply decline delivery or initiate a return within 7 days of delivery."
        ),
    },
    "contact": {
        "title": "Customer Support & Concierge",
        "summary": (
            "Cartivo Concierge is available 24/7 via this AI Shopping Assistant. "
            "For human assistance, email us at support@cartivo.com or call +91-1800-CARTIVO (Mon-Sat, 9:00 AM - 7:00 PM IST)."
        ),
        "email": "support@cartivo.com",
        "phone": "+91-1800-CARTIVO",
        "hours": "Mon-Sat, 9:00 AM - 7:00 PM IST",
    },
}


# ==============================================================================
# 3. FREQUENTLY ASKED QUESTIONS (FAQS)
# ==============================================================================

STORE_FAQS = [
    {
        "keywords": ["cod", "cash on delivery", "cash"],
        "topic": "payment_methods",
        "answer": "Yes! Cash on Delivery (COD) is available across all serviceable pin codes in India with no extra convenience charge."
    },
    {
        "keywords": ["upi", "gpay", "phonepe", "paytm", "online payment"],
        "topic": "payment_methods",
        "answer": "We accept all UPI apps (Google Pay, PhonePe, Paytm, BHIM) along with Credit/Debit cards (Visa, MasterCard, RuPay) and Net Banking."
    },
    {
        "keywords": ["shipping", "delivery time", "how long", "courier", "when will it arrive", "delivery charges"],
        "topic": "shipping",
        "answer": "Orders are typically delivered within 2-4 business days. Shipping is FREE on orders above ₹999. For orders under ₹999, shipping is ₹49."
    },
    {
        "keywords": ["return", "return policy", "replace", "exchange", "how to return"],
        "topic": "return",
        "answer": "We provide a 7-day hassle-free return window. You can initiate a return from your Orders page (/orders/). We offer free doorstep pickup."
    },
    {
        "keywords": ["refund", "money back", "refund time", "when will i get refund"],
        "topic": "refund",
        "answer": "Refunds are processed within 24-48 hours after item inspection and credited back within 3-5 business days."
    },
    {
        "keywords": ["cancel", "cancellation", "cancel order"],
        "topic": "cancellation",
        "answer": "You can cancel your order from your Orders page (/orders/) before it is packed or shipped. If it has already shipped, you can refuse delivery."
    },
    {
        "keywords": ["authentic", "genuine", "original", "warranty"],
        "topic": "contact",
        "answer": "All items on Cartivo are 100% genuine and sourced directly from verified brands and manufacturers, backed by full warranty."
    },
]


def match_policy_or_faq(query: str) -> str:
    """
    Finds the most relevant static store policy or FAQ response for a user's inquiry.
    Returns empty string if no relevant static policy is matched.
    """
    query_lower = query.lower().strip()

    # Direct topic matches
    if any(k in query_lower for k in ["shipping", "delivery charges", "free shipping", "delivery time", "delivery partner"]):
        return STORE_POLICIES["shipping"]["summary"]
    if any(k in query_lower for k in ["return policy", "return item", "how to return", "7 day return", "exchange"]):
        return STORE_POLICIES["return"]["summary"]
    if any(k in query_lower for k in ["refund policy", "refund time", "money back", "refund status"]):
        return STORE_POLICIES["refund"]["summary"]
    if any(k in query_lower for k in ["payment method", "how to pay", "accept upi", "accept card", "cod available", "cash on delivery"]):
        return STORE_POLICIES["payment_methods"]["summary"]
    if any(k in query_lower for k in ["cancel order", "cancellation policy", "how to cancel"]):
        return STORE_POLICIES["cancellation"]["summary"]
    if any(k in query_lower for k in ["customer care", "support email", "helpline", "contact number", "support phone"]):
        return STORE_POLICIES["contact"]["summary"]

    # Keyword search across FAQ table
    for faq in STORE_FAQS:
        for kw in faq["keywords"]:
            if kw in query_lower:
                return faq["answer"]

    return ""
