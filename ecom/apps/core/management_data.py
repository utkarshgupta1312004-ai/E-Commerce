"""
Static definition and registry for all 20 internal management departments.
Used by seed commands and department dashboard fallback rendering.
"""

DEPARTMENTS_DATA = [
    {
        "name": "Account Management",
        "slug": "accounts",
        "code": "accounts",
        "description": "Manage users, staff credentials, roles, profiles, and access permissions.",
        "icon": "users",
        "accent_color": "blue",
        "display_order": 1,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "All Users", "icon": "user", "section": "users"},
            {"name": "Staff & Managers", "icon": "user-check", "section": "staff"},
            {"name": "Roles & Permissions", "icon": "shield", "section": "roles"},
            {"name": "Activity Logins", "icon": "key-round", "section": "logins"},
        ],
        "kpis": [
            {"label": "Total Users", "value": "1,248", "change": "+12%", "trend": "up"},
            {"label": "Active Staff", "value": "14", "change": "+2", "trend": "up"},
            {"label": "Management Roles", "value": "5", "change": "0", "trend": "neutral"},
            {"label": "Active Sessions", "value": "32", "change": "+5%", "trend": "up"},
        ]
    },
    {
        "name": "Catalog Management",
        "slug": "catalog",
        "code": "catalog",
        "description": "Control product listings, category taxonomy, brands, attributes, and variants.",
        "icon": "shopping-bag",
        "accent_color": "indigo",
        "display_order": 2,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Products", "icon": "tag", "section": "products"},
            {"name": "Categories", "icon": "folder-tree", "section": "categories"},
            {"name": "Brands", "icon": "award", "section": "brands"},
            {"name": "Product Variants", "icon": "copy", "section": "variants"},
        ],
        "kpis": [
            {"label": "Active Products", "value": "342", "change": "+8", "trend": "up"},
            {"label": "Categories", "value": "14", "change": "0", "trend": "neutral"},
            {"label": "Featured Items", "value": "28", "change": "+3", "trend": "up"},
            {"label": "Out of Stock", "value": "6", "change": "-2", "trend": "down"},
        ]
    },
    {
        "name": "Inventory Management",
        "slug": "inventory",
        "code": "inventory",
        "description": "Track warehouse stock levels, low-stock alerts, reservations, and stock movements.",
        "icon": "package",
        "accent_color": "emerald",
        "display_order": 3,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Stock Levels", "icon": "boxes", "section": "stock"},
            {"name": "Warehouses", "icon": "warehouse", "section": "warehouses"},
            {"name": "Stock Movements", "icon": "arrow-left-right", "section": "movements"},
            {"name": "Reorder Alerts", "icon": "alert-triangle", "section": "alerts"},
        ],
        "kpis": [
            {"label": "Total Stock Units", "value": "18,450", "change": "+350", "trend": "up"},
            {"label": "Low Stock Alerts", "value": "9", "change": "-3", "trend": "down"},
            {"label": "Warehouses", "value": "3", "change": "Active", "trend": "neutral"},
            {"label": "Stock Value", "value": "₹42.8L", "change": "+4.1%", "trend": "up"},
        ]
    },
    {
        "name": "Search Management",
        "slug": "search",
        "code": "search",
        "description": "Configure search synonyms, boost rules, indexed keywords, and zero-result queries.",
        "icon": "search",
        "accent_color": "cyan",
        "display_order": 4,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Popular Queries", "icon": "trending-up", "section": "queries"},
            {"name": "Synonym Rules", "icon": "split", "section": "synonyms"},
            {"name": "Zero-Result Searches", "icon": "search-x", "section": "zero_results"},
            {"name": "Index Health", "icon": "cpu", "section": "index_health"},
        ],
        "kpis": [
            {"label": "Daily Searches", "value": "3,820", "change": "+18%", "trend": "up"},
            {"label": "Search CTR", "value": "64.2%", "change": "+2.4%", "trend": "up"},
            {"label": "Zero Result Rate", "value": "3.1%", "change": "-0.8%", "trend": "down"},
            {"label": "Active Synonyms", "value": "142", "change": "+10", "trend": "up"},
        ]
    },
    {
        "name": "Cart Management",
        "slug": "cart",
        "code": "cart",
        "description": "Monitor active customer carts, abandoned cart recovery, and cart item insights.",
        "icon": "shopping-cart",
        "accent_color": "amber",
        "display_order": 5,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Active Carts", "icon": "shopping-cart", "section": "active_carts"},
            {"name": "Abandoned Carts", "icon": "clock", "section": "abandoned"},
            {"name": "Recovery Campaigns", "icon": "mail-check", "section": "recovery"},
            {"name": "Cart Settings", "icon": "settings", "section": "cart_settings"},
        ],
        "kpis": [
            {"label": "Active Carts", "value": "184", "change": "+14", "trend": "up"},
            {"label": "Abandoned Carts", "value": "42", "change": "-6", "trend": "down"},
            {"label": "Cart Value Total", "value": "₹8.9L", "change": "+7.5%", "trend": "up"},
            {"label": "Cart-to-Checkout", "value": "48.6%", "change": "+3.1%", "trend": "up"},
        ]
    },
    {
        "name": "Wishlist Management",
        "slug": "wishlist",
        "code": "wishlist",
        "description": "Analyze saved customer wishlists, trending saved products, and conversion opportunities.",
        "icon": "heart",
        "accent_color": "rose",
        "display_order": 6,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Customer Wishlists", "icon": "list", "section": "wishlists"},
            {"name": "Most Desired Products", "icon": "star", "section": "top_items"},
            {"name": "Back-in-Stock Alerts", "icon": "bell", "section": "alerts"},
            {"name": "Conversion Reports", "icon": "bar-chart-2", "section": "reports"},
        ],
        "kpis": [
            {"label": "Total Saved Items", "value": "4,120", "change": "+230", "trend": "up"},
            {"label": "Active Wishlists", "value": "890", "change": "+45", "trend": "up"},
            {"label": "Wishlist Conversion", "value": "19.4%", "change": "+1.8%", "trend": "up"},
            {"label": "Price Drop Alerts", "value": "156", "change": "+22", "trend": "up"},
        ]
    },
    {
        "name": "Checkout Management",
        "slug": "checkout",
        "code": "checkout",
        "description": "Configure checkout workflows, address validations, shipping selectors, and funnel health.",
        "icon": "credit-card",
        "accent_color": "blue",
        "display_order": 7,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Active Sessions", "icon": "activity", "section": "sessions"},
            {"name": "Funnel Drop-offs", "icon": "filter", "section": "funnel"},
            {"name": "Address Rules", "icon": "map-pin", "section": "address_rules"},
            {"name": "Checkout Config", "icon": "sliders", "section": "config"},
        ],
        "kpis": [
            {"label": "Funnel Completion", "value": "78.2%", "change": "+2.5%", "trend": "up"},
            {"label": "Active Checkouts", "value": "23", "change": "+4", "trend": "up"},
            {"label": "Avg. Step Time", "value": "1m 42s", "change": "-12s", "trend": "up"},
            {"label": "Drop-off Rate", "value": "21.8%", "change": "-2.5%", "trend": "down"},
        ]
    },
    {
        "name": "Payment Management",
        "slug": "payments",
        "code": "payments",
        "description": "Manage payment gateway integrations, transaction logs, refunds, and reconciliation.",
        "icon": "dollar-sign",
        "accent_color": "emerald",
        "display_order": 8,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Transactions", "icon": "receipt", "section": "transactions"},
            {"name": "Refund Requests", "icon": "rotate-ccw", "section": "refunds"},
            {"name": "Payment Gateways", "icon": "credit-card", "section": "gateways"},
            {"name": "Reconciliation", "icon": "file-check", "section": "reconciliation"},
        ],
        "kpis": [
            {"label": "Volume (Today)", "value": "₹1.48L", "change": "+15.2%", "trend": "up"},
            {"label": "Success Rate", "value": "99.2%", "change": "+0.4%", "trend": "up"},
            {"label": "Pending Refunds", "value": "2", "change": "-1", "trend": "down"},
            {"label": "Failed Transactions", "value": "3", "change": "-2", "trend": "down"},
        ]
    },
    {
        "name": "Order Management",
        "slug": "orders",
        "code": "orders",
        "description": "Process incoming orders, status transitions, invoices, cancellations, and order histories.",
        "icon": "clipboard-list",
        "accent_color": "purple",
        "display_order": 9,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "All Orders", "icon": "list-ordered", "section": "all_orders"},
            {"name": "Pending Approval", "icon": "clock", "section": "pending"},
            {"name": "Invoices", "icon": "file-text", "section": "invoices"},
            {"name": "Returns & Cancels", "icon": "ban", "section": "cancellations"},
        ],
        "kpis": [
            {"label": "Orders (Today)", "value": "64", "change": "+14", "trend": "up"},
            {"label": "Pending Processing", "value": "11", "change": "-3", "trend": "down"},
            {"label": "Average Order Value", "value": "₹2,310", "change": "+₹180", "trend": "up"},
            {"label": "Fulfillment SLA", "value": "98.8%", "change": "+0.5%", "trend": "up"},
        ]
    },
    {
        "name": "Shipping Management",
        "slug": "shipping",
        "code": "shipping",
        "description": "Configure shipping carriers, rates, postal delivery zones, tracking, and courier webhooks.",
        "icon": "truck",
        "accent_color": "cyan",
        "display_order": 10,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Active Shipments", "icon": "truck", "section": "shipments"},
            {"name": "Courier Partners", "icon": "send", "section": "couriers"},
            {"name": "Delivery Zones", "icon": "globe", "section": "zones"},
            {"name": "Tracking Sync", "icon": "refresh-cw", "section": "tracking"},
        ],
        "kpis": [
            {"label": "In-Transit", "value": "88", "change": "+16", "trend": "up"},
            {"label": "Delivered Today", "value": "42", "change": "+8", "trend": "up"},
            {"label": "On-Time Rate", "value": "97.4%", "change": "+1.1%", "trend": "up"},
            {"label": "Delayed Shipments", "value": "2", "change": "0", "trend": "neutral"},
        ]
    },
    {
        "name": "Fulfillment Management",
        "slug": "fulfillment",
        "code": "fulfillment",
        "description": "Oversee warehouse pick lists, packing stations, dispatch batches, and return inspections.",
        "icon": "check-square",
        "accent_color": "amber",
        "display_order": 11,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Picking Queue", "icon": "list-checks", "section": "picking"},
            {"name": "Packing Stations", "icon": "box", "section": "packing"},
            {"name": "Ready to Ship", "icon": "package-check", "section": "ready_to_ship"},
            {"name": "Return Inspection", "icon": "undo-2", "section": "returns"},
        ],
        "kpis": [
            {"label": "Awaiting Picking", "value": "15", "change": "-4", "trend": "down"},
            {"label": "Currently Packing", "value": "8", "change": "+2", "trend": "up"},
            {"label": "Packed & Ready", "value": "24", "change": "+7", "trend": "up"},
            {"label": "Avg Pack Time", "value": "4m 10s", "change": "-25s", "trend": "up"},
        ]
    },
    {
        "name": "Promotion Management",
        "slug": "promotions",
        "code": "promotions",
        "description": "Create discount coupons, BOGO rules, promotional campaigns, and voucher limits.",
        "icon": "percent",
        "accent_color": "rose",
        "display_order": 12,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Coupon Codes", "icon": "ticket", "section": "coupons"},
            {"name": "Flash Sale Rules", "icon": "zap", "section": "flash_sales"},
            {"name": "Campaign Budgets", "icon": "wallet", "section": "budgets"},
            {"name": "Redemption Logs", "icon": "history", "section": "redemptions"},
        ],
        "kpis": [
            {"label": "Active Coupons", "value": "8", "change": "+2", "trend": "up"},
            {"label": "Redemptions Today", "value": "134", "change": "+28", "trend": "up"},
            {"label": "Discount Value", "value": "₹34,200", "change": "+18%", "trend": "up"},
            {"label": "Promo ROI", "value": "4.8x", "change": "+0.3x", "trend": "up"},
        ]
    },
    {
        "name": "Review Management",
        "slug": "reviews",
        "code": "reviews",
        "description": "Moderate customer ratings, approve verified buyer reviews, and flag inappropriate content.",
        "icon": "star",
        "accent_color": "amber",
        "display_order": 13,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Moderation Queue", "icon": "clock", "section": "moderation"},
            {"name": "Approved Reviews", "icon": "check-circle", "section": "approved"},
            {"name": "Flagged & Reported", "icon": "flag", "section": "flagged"},
            {"name": "Rating Analytics", "icon": "bar-chart", "section": "analytics"},
        ],
        "kpis": [
            {"label": "Pending Reviews", "value": "7", "change": "-5", "trend": "down"},
            {"label": "Average Rating", "value": "4.82 / 5", "change": "+0.04", "trend": "up"},
            {"label": "Approved Reviews", "value": "1,890", "change": "+42", "trend": "up"},
            {"label": "Reported Reviews", "value": "1", "change": "-1", "trend": "down"},
        ]
    },
    {
        "name": "Notification Management",
        "slug": "notifications",
        "code": "notifications",
        "description": "Configure transactional email templates, SMS alerts, browser push, and delivery logs.",
        "icon": "bell",
        "accent_color": "blue",
        "display_order": 14,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Email Templates", "icon": "mail", "section": "email_templates"},
            {"name": "SMS Gateway", "icon": "message-square", "section": "sms"},
            {"name": "Push Dispatches", "icon": "radio", "section": "push"},
            {"name": "Delivery Logs", "icon": "activity", "section": "logs"},
        ],
        "kpis": [
            {"label": "Dispatches Today", "value": "2,410", "change": "+180", "trend": "up"},
            {"label": "Delivery Rate", "value": "99.4%", "change": "+0.1%", "trend": "up"},
            {"label": "Open Rate (Email)", "value": "42.8%", "change": "+2.1%", "trend": "up"},
            {"label": "Bounces / Errors", "value": "6", "change": "-2", "trend": "down"},
        ]
    },
    {
        "name": "Recommendation Management",
        "slug": "recommendations",
        "code": "recommendations",
        "description": "Configure AI recommendation algorithms, cross-sell/upsell rules, and CTR analytics.",
        "icon": "sparkles",
        "accent_color": "purple",
        "display_order": 15,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Recommendation Rules", "icon": "git-merge", "section": "rules"},
            {"name": "Cross-sell Pairings", "icon": "layers", "section": "cross_sell"},
            {"name": "AI Model Weights", "icon": "sliders", "section": "models"},
            {"name": "CTR Performance", "icon": "trending-up", "section": "performance"},
        ],
        "kpis": [
            {"label": "Attributed Revenue", "value": "₹3.85L", "change": "+22%", "trend": "up"},
            {"label": "Click-Through Rate", "value": "12.8%", "change": "+1.4%", "trend": "up"},
            {"label": "Active Pairing Rules", "value": "34", "change": "+4", "trend": "up"},
            {"label": "AI Recommendation Hit", "value": "89.2%", "change": "+0.8%", "trend": "up"},
        ]
    },
    {
        "name": "CMS Management",
        "slug": "cms",
        "code": "cms",
        "description": "Manage navigation bars, category sub-menus, promotional hero banners, and static pages.",
        "icon": "layout",
        "accent_color": "indigo",
        "display_order": 16,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Hero Banners", "icon": "image", "section": "banners"},
            {"name": "Navbar Items", "icon": "navigation", "section": "navbar"},
            {"name": "Category Sub-Nav", "icon": "layout-grid", "section": "categories"},
            {"name": "Homepage Sections", "icon": "component", "section": "sections"},
            {"name": "Trust Badges", "icon": "shield-check", "section": "badges"},
        ],
        "kpis": [
            {"label": "Active Banners", "value": "5", "change": "0", "trend": "neutral"},
            {"label": "Sub-Nav Categories", "value": "14", "change": "Active", "trend": "neutral"},
            {"label": "Homepage Sections", "value": "6", "change": "0", "trend": "neutral"},
            {"label": "Trust Badges", "value": "4", "change": "0", "trend": "neutral"},
        ]
    },
    {
        "name": "Analytics Management",
        "slug": "analytics",
        "code": "analytics",
        "description": "Monitor store sales volume, conversion metrics, customer acquisition, and export reports.",
        "icon": "bar-chart-3",
        "accent_color": "emerald",
        "display_order": 17,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Sales Analytics", "icon": "trending-up", "section": "sales"},
            {"name": "Customer Acquisition", "icon": "user-plus", "section": "acquisition"},
            {"name": "Product Performance", "icon": "package", "section": "product_perf"},
            {"name": "Export Reports", "icon": "download", "section": "reports"},
        ],
        "kpis": [
            {"label": "Monthly Revenue", "value": "₹38.4L", "change": "+14.6%", "trend": "up"},
            {"label": "Total Orders", "value": "1,420", "change": "+8.2%", "trend": "up"},
            {"label": "Conversion Rate", "value": "3.48%", "change": "+0.32%", "trend": "up"},
            {"label": "New Customers", "value": "340", "change": "+18%", "trend": "up"},
        ]
    },
    {
        "name": "Support Management",
        "slug": "support",
        "code": "support",
        "description": "Handle customer helpdesk tickets, dispute escalations, live inquiries, and knowledge base.",
        "icon": "headphones",
        "accent_color": "blue",
        "display_order": 18,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Open Tickets", "icon": "inbox", "section": "open_tickets"},
            {"name": "Assigned to Me", "icon": "user", "section": "assigned"},
            {"name": "Resolved Archive", "icon": "check-circle", "section": "resolved"},
            {"name": "Knowledge Base", "icon": "book-open", "section": "kb"},
        ],
        "kpis": [
            {"label": "Open Tickets", "value": "9", "change": "-3", "trend": "down"},
            {"label": "First Response Avg", "value": "14m", "change": "-3m", "trend": "up"},
            {"label": "Customer CSAT", "value": "96.2%", "change": "+1.4%", "trend": "up"},
            {"label": "Resolved Today", "value": "18", "change": "+4", "trend": "up"},
        ]
    },
    {
        "name": "Audit & Security Management",
        "slug": "audit",
        "code": "audit",
        "description": "Inspect administrative actions, staff logins, permission elevation, and security incident logs.",
        "icon": "shield-alert",
        "accent_color": "rose",
        "display_order": 19,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Staff Login Logs", "icon": "key", "section": "logins"},
            {"name": "Access Violations", "icon": "alert-octagon", "section": "violations"},
            {"name": "Administrative Actions", "icon": "edit-3", "section": "actions"},
            {"name": "Security Policies", "icon": "lock", "section": "policies"},
        ],
        "kpis": [
            {"label": "Total Audit Logs", "value": "Live", "change": "Real-time", "trend": "neutral"},
            {"label": "Staff Logins (24h)", "value": "12", "change": "Normal", "trend": "neutral"},
            {"label": "Failed Attempts", "value": "0", "change": "Safe", "trend": "down"},
            {"label": "Access Denied", "value": "0", "change": "Clear", "trend": "down"},
        ]
    },
    {
        "name": "System Settings Management",
        "slug": "settings",
        "code": "settings",
        "description": "Configure store-wide profile, payment API keys, email SMTP, sessions, and maintenance mode.",
        "icon": "settings",
        "accent_color": "slate",
        "display_order": 20,
        "sidebar_menu": [
            {"name": "Dashboard", "icon": "layout-dashboard", "section": "overview"},
            {"name": "Store Profile", "icon": "store", "section": "store"},
            {"name": "Email & SMTP", "icon": "mail", "section": "email"},
            {"name": "Security & Sessions", "icon": "shield-check", "section": "security"},
            {"name": "Maintenance Mode", "icon": "tool", "section": "maintenance"},
        ],
        "kpis": [
            {"label": "Store Status", "value": "Online", "change": "100% Uptime", "trend": "up"},
            {"label": "Environment", "value": "Development", "change": "Debug Active", "trend": "neutral"},
            {"label": "Database Engine", "value": "SQLite 3", "change": "Connected", "trend": "up"},
            {"label": "Security Health", "value": "Optimal", "change": "CSRF Active", "trend": "up"},
        ]
    },
]


def get_department_config(slug):
    """Retrieve metadata configuration for a department by slug."""
    for dept in DEPARTMENTS_DATA:
        if dept["slug"] == slug:
            return dept
    return None
