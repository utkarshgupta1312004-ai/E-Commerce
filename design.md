# Design System & UI Styleguide

## Project: Cartivo &bull; Modern E-Commerce Platform
**Tagline:** "Shop Smarter. Live Better."

---

## 1. Brand Identity & Logo Assets
- **Brand Name:** **Cartivo**
- **Logo Graphic:** Stylized speed shopping cart with aerodynamic trailing motion bars and warm sunrise orange/amber gradient bowl supported on a dark navy frame and wheels.
- **Logo Assets in `static/images/`:**
  - `cartivo-logo.png`: Full master vertical logo with emblem, "Cartivo" wordmark, and tagline.
  - `cartivo-horizontal.png`: Optimized horizontal lockup for desktop/mobile headers and sticky navigation.
  - `cartivo-icon.png`: Standalone shopping cart emblem for avatars, app icons, and loading states.
  - `favicon.ico`: Multi-size browser favicon (16x16, 32x32, 48x48, 64x64).
  - `favicon.png`: High-resolution 192x192 PNG favicon for modern browsers and mobile home screens.


## 1. Aesthetic Vision & Design Philosophy

The visual design is engineered around a **Modern Luxury-Minimalist & High-Conversion** aesthetic. Inspired by top-tier contemporary commerce experiences (such as Apple, Linear, and Stripe), it emphasizes:
- **Clarity over Clutter:** Generous whitespace, razor-sharp typographic hierarchy, and clear calls-to-action.
- **Micro-Animations & Depth:** Soft multi-layered elevation shadows, smooth state transitions, and responsive hover feedback.
- **Responsive Fluidity:** Adaptive layouts providing an app-like experience across desktop, tablet, and mobile displays.

---

## 2. Color Palette & Semantic Design Tokens

### 2.1. Core Color System

| Token Name | Hex Code | HSL Value | Purpose & Usage |
| :--- | :--- | :--- | :--- |
| `--color-brand-primary` | `#0F172A` | `hsl(222, 47%, 11%)` | Midnight Navy / Primary brand tone, header accents, primary buttons |
| `--color-brand-accent` | `#2563EB` | `hsl(217, 91%, 60%)` | Electric Royal Blue / Active states, links, checkout highlights, CTAs |
| `--color-brand-accent-hover`| `#1D4ED8` | `hsl(224, 76%, 48%)` | Darkened accent for hover & active states |
| `--color-gold-sale` | `#D97706` | `hsl(38, 92%, 50%)` | Amber Gold / Promotional banners, discount tags, star ratings |

### 2.2. Neutral & Surface Scale (Light Mode Default)

| Token Name | Hex Code | Purpose |
| :--- | :--- | :--- |
| `--color-bg-canvas` | `#F8FAFC` | Main application background (soft off-white) |
| `--color-bg-surface` | `#FFFFFF` | Card backgrounds, modal windows, table rows, dropdowns |
| `--color-bg-muted` | `#F1F5F9` | Input fields background, secondary buttons, badge pills |
| `--color-border-subtle` | `#E2E8F0` | Card borders, dividers, table borders |
| `--color-border-focus` | `#3B82F6` | Input focus outline and active ring |
| `--color-text-primary` | `#0F172A` | Headings, titles, price values, high-contrast text |
| `--color-text-secondary`| `#475569` | Body copy, product descriptions, secondary meta text |
| `--color-text-muted` | `#94A3B8` | Timestamps, placeholder text, breadcrumbs |
| `--color-text-inverse` | `#FFFFFF` | Text on dark buttons and badges |

### 2.3. Feedback & Status Colors

| State | Background Tint | Border / Accent | Text Color | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Success** | `#ECFDF5` | `#10B981` | `#065F46` | "In Stock", "Payment Successful", "Delivered" |
| **Warning** | `#FFFBEB` | `#F59E0B` | `#92400E` | "Only 2 items left", "Pending Review" |
| **Danger** | `#FEF2F2` | `#EF4444` | `#991B1B` | "Out of Stock", "Payment Failed", "Cancelled" |
| **Info** | `#EFF6FF` | `#3B82F6` | `#1E40AF` | "Free Shipping Applied", System announcements |

---

## 3. Typography Hierarchy

### 3.1. Font Families
- **Primary Body & Display Font:** `'Poppins'`, from Google Fonts (`fonts.googleapis.com`), fallback `sans-serif`.
  - Import URL: `https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap`
  - Integrated directly as default font family in Tailwind CSS v4 `@theme { --font-sans: 'Poppins', sans-serif; }`.
- **Monospace (SKUs, Order IDs, Invoices):** `'JetBrains Mono'`, `'Fira Code', monospace`


### 3.2. Type Scale

| Role | Font Size | Line Height | Weight | Letter Spacing | CSS Variable |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display Hero** | `3.5rem` (56px) | `1.1` | 800 (ExtraBold) | `-0.025em` | `--font-display` |
| **Heading 1** | `2.5rem` (40px) | `1.2` | 700 (Bold) | `-0.02em` | `--font-h1` |
| **Heading 2** | `2.0rem` (32px) | `1.25`| 700 (Bold) | `-0.015em` | `--font-h2` |
| **Heading 3** | `1.5rem` (24px) | `1.3` | 600 (SemiBold) | `-0.01em` | `--font-h3` |
| **Heading 4** | `1.25rem` (20px)| `1.4` | 600 (SemiBold) | `0em` | `--font-h4` |
| **Body Large** | `1.125rem` (18px)| `1.6` | 400 / 500 | `0em` | `--font-body-lg` |
| **Body Default** | `1.0rem` (16px) | `1.5` | 400 (Regular) | `0em` | `--font-body` |
| **Body Small** | `0.875rem` (14px)| `1.5` | 400 / 500 | `0em` | `--font-body-sm` |
| **Caption / Micro**| `0.75rem` (12px)| `1.4` | 500 (Medium) | `+0.02em` | `--font-caption` |

---

## 4. Spacing, Borders & Elevation Tokens

### 4.1. Spacing Scale (Base 4px / 8px Grid)
```css
:root {
  --space-1: 0.25rem;  /* 4px  */
  --space-2: 0.5rem;   /* 8px  */
  --space-3: 0.75rem;  /* 12px */
  --space-4: 1.0rem;   /* 16px */
  --space-5: 1.25rem;  /* 20px */
  --space-6: 1.5rem;   /* 24px */
  --space-8: 2.0rem;   /* 32px */
  --space-12: 3.0rem;  /* 48px */
  --space-16: 4.0rem;  /* 64px */
}
```

### 4.2. Border Radius Tokens
```css
:root {
  --radius-sm: 6px;    /* Badges, micro tags */
  --radius-md: 10px;   /* Buttons, input fields */
  --radius-lg: 16px;   /* Product cards, modal dialogs */
  --radius-xl: 24px;   /* Hero containers, banners */
  --radius-full: 9999px; /* Pill buttons, avatars */
}
```

### 4.3. Elevation Shadows
```css
:root {
  --shadow-subtle: 0 1px 2px 0 rgba(15, 23, 42, 0.05);
  --shadow-card:   0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04);
  --shadow-hover:  0 12px 24px -4px rgba(15, 23, 42, 0.12), 0 4px 8px -4px rgba(15, 23, 42, 0.06);
  --shadow-modal:  0 25px 50px -12px rgba(15, 23, 42, 0.25);
}
```

---

## 5. Key UI Component Specifications

### 5.1. Buttons
- **Primary Button:** Background `--color-brand-primary`, text white, padding `0.75rem 1.5rem`, border-radius `--radius-md`, subtle hover translation `translateY(-1px)` and box shadow.
- **Accent Button (CTA / Buy Now):** Background `--color-brand-accent`, text white, bold font weight.
- **Secondary / Outline Button:** Background transparent, border `1.5px solid --color-border-subtle`, text `--color-text-primary`, hover background `--color-bg-muted`.
- **Icon Button:** Square `40px x 40px`, centered SVG icon, rounded circle or `--radius-md`.

### 5.2. Product Cards
- Aspect ratio of image container: `4:5` or `1:1` with `object-fit: cover`.
- Subtle hover zoom on image (`transform: scale(1.04); transition: 300ms ease;`).
- Floating wishlist heart button in top-right corner with smooth fill animation on toggle.
- Category micro-tag, title (clamped to 2 lines), star rating review count, and price layout (`current price` bold + `original strike-through price`).
- "Add to Cart" quick-action button revealed on desktop hover or pinned on mobile.

### 5.3. Form Inputs & Controls
- Height: `44px` (touch-friendly on mobile).
- Border: `1.5px solid --color-border-subtle`.
- Focus state: Border color `--color-brand-accent` with a `0 0 0 3px rgba(37, 99, 235, 0.15)` focus ring.
- Error state: Border color `--color-border-danger` with helper text below in red.

### 5.4. Slide-Over Cart Drawer & Mobile Navigation Drawer
- Width: `420px` (or `100vw` on mobile).
- Slide-in with dark backdrop overlay (`rgba(15, 23, 42, 0.5)`).
- Mobile Drawer: Quick access to Categories, Collections, Sale tags, and Account links.
- Mobile Bottom Navigation Bar: Fixed bottom bar (`md:hidden`) with Home, Shop, Wishlist, Bag, and Account icons for native app feel.

### 5.5. Category Sub-Menu Bar (Directly Below Navbar)
- **Placement:** Immediately below sticky navigation header (`sticky top-16 sm:top-20 z-30`).
- **Design & Layout:**
  - Clean white surface with subtle bottom border (`border-b border-slate-200`) and shadow.
  - Horizontally scrollable without scrollbars (`no-scrollbar`).
  - Visual items matching category screenshot: Rounded icon square (`w-10 h-10 rounded-xl`) with amber icon highlights and smooth scaling on hover (`group-hover:scale-105`).
  - 14 Categories: For You, Fashion, Mobiles, Electronics, Beauty, Home, Appliances, Toys & Baby, Food & Grocery, Auto Acc., Sports & Fitness, Furniture, Books & Media, 2 Wheelers.
  - Active State: Vibrant blue indicator line (`h-0.5 bg-blue-600 rounded-full`) under active tab with blue highlighted icon container (`bg-blue-50 text-blue-600`).

### 5.6. Flipkart-Style Promotional Offer Banners (Continuous Animated Infinite Loop)
- **Placement:** Directly below Category Sub-Menu Bar.
- **Card Anatomy & Dimensions:**
  - Card Dimensions: Landscape aspect ratio (`w-[300px] sm:w-[460px] md:w-[520px] lg:w-[560px] xl:w-[580px] h-[190px] sm:h-[220px] md:h-[235px]`) with `rounded-3xl` corners.
  - Multi-card view: Shows ~2.2 to 2.5 cards on desktop screens with smooth continuous movement; 1 full card + peek on mobile.
  - Campaign Badge: Scalloped yellow starburst/stamp badge (`bg-amber-400 text-blue-950 font-black text-[9px] sm:text-[10px] uppercase`) with lightning icon: **BIG BACHAT DAYS**.
  - Typography: Punchy bold headlines and prices (e.g. `VIRAT V1 5G From ₹14,499`, `Ortho slippers Under ₹399`, `Best fragrance picks Min. 50% Off`, `Studio Wireless ANC Flat 45% Off`, `Smart Chronographs Under ₹2,999`).
  - Bank Offer Pill: Floating white pill tag with bank emblem (`PNB Up to ₹4,200 Instant Discount*`, `HDFC Flat 10% Instant Cashback*`, `No-Cost EMI Available*`).
  - Product Cutout / Framed Image: High-resolution angled product showcase on the right side with smooth zoom (`group-hover/card:scale-108 transition-transform duration-500`).
- **Continuous Infinite Animation Mechanics:**
  - **Animation Track:** `.animate-marquee-smooth` running a silky 40s linear infinite CSS marquee (`translateX(0%)` to `translateX(-50%)`).
  - **Seamless Loop:** 5 primary promotional banners + 5 duplicate banners (`aria-hidden="true"`) for zero-jump, perpetual horizontal scrolling.
  - **Interaction:** Hover or touch pauses the animation immediately (`animation-play-state: paused`) allowing users to comfortably read deals and click links.
  - **Ambient Masks:** Left and right gradient fade masks (`from-slate-100 to-transparent`) for seamless viewport edge transitions.

---

## 6. Loading States & Micro-Animations

### 6.1. Skeleton Shimmer Loading (Images)
- **Placeholder:** Containers show a pulsing gradient sweep (`shimmer-effect` with `linear-gradient` sweep across `rgba(255, 255, 255, 0.4)`).
- **Reveal Transition:** On native `onload`, images transition from `opacity-0` to full opacity via `transition-opacity duration-700 ease-out`, smoothly hiding the underlying skeleton.

### 6.2. Text & Content Entrance Animations
- **Fade-In-Up:** Staggered entrance animation (`animate-fade-in-up`) translating `16px` up with cubic-bezier easing (`0.16, 1, 0.3, 1`).
- **Pulse Indicators:** Subtly pulsating notification dots on announcement pills and badges.

---

## 7. Responsive Breakpoint Standards

| Device Class | Viewport Width | Key Layout Adaptations |
| :--- | :--- | :--- |
| **Mobile (Phones)** | `< 640px` | 2-column product grid, stacked hero buttons, slide-out drawer, fixed bottom navigation bar, expandable search |
| **Tablet (iPads)** | `640px - 1023px` | 2x2 category grid, 3-column product grid, top navigation with hamburger menu, inline search input |
| **Desktop / Wide** | `≥ 1024px` | 4-column product grid, full horizontal desktop menu, expanded search bar, ambient glow hero layout |

---

## 8. Executive Dark Theme Design Tokens (Superadmin Suite)

The administrative console uses an executive dark theme optimized for continuous operational monitoring, high readability, and reduced eye strain:

### 8.1. Color Tokens

| Token Name | Hex Code | Purpose & Usage |
| :--- | :--- | :--- |
| `--bg-canvas` | `#0B0F19` | Deep obsidian background for maximum contrast |
| `--bg-sidebar` | `#0F172A` | Slate-900 sidebar tone matching header |
| `--bg-header` | `#0F172A` | Sticky top navigation bar |
| `--bg-card` | `#131C2E` | Card surface with subtle border |
| `--bg-card-hover` | `#172338` | Hover state for interactive cards |
| `--border-subtle` | `#1E293B` | Slate-800 borders, dividers, table lines |
| `--accent-indigo` | `#6366F1` | Primary action accents, active pagination pills, key metrics |
| `--accent-cyan` | `#06B6D4` | Storefront view links, secondary charts, code badges |
| `--accent-emerald` | `#10B981` | Positive trends, nominal operational SLAs, settled orders |
| `--accent-amber` | `#F59E0B` | Superadmin privilege badges, warnings, security stream alerts |

### 8.2. Table Typography & Formatting Guidelines
- **Disciplined Column Widths:** Always enforce explicit widths (`w-12`, `min-w-[240px]`, `w-36`, `w-44`, etc.) to prevent layout wobble or unexpected text wrapping across viewports.
- **Micro-Badges for Metadata:** Pair primary bold titles with small chip badges (e.g. `dept.badge`) to communicate domain roles compactly.
- **Code Namespace Pills:** Monospaced identifiers (`apps/catalog`, `#ORD-98214`) formatted with high-contrast background and borders.
- **Semantic Category Badges:** Color-code category tags (Core Commerce: Blue, Operations: Purple, Payments: Emerald, Marketing: Cyan).

---

## 9. Printing & Document Export Standards

All administrative data tables adhere to unified `@media print` rules:
- **Clean Background:** Background forced to `#FFFFFF` with `#0F172A` text color for high contrast and ink savings.
- **Chrome Suppression:** Sidebar, header, navigation controls, search inputs, pagination buttons, and action buttons hidden via `.no-print` and `.pagination-controls`.
- **Complete List Printing:** Table pagination is temporarily bypassed during print so the generated document contains the complete ledger.
- **Multi-Page Support:** Repeating headers (`thead { display: table-header-group; }`) and row break prevention (`tr { page-break-inside: avoid; }`).
- **Document Headers:** Formal print document titles with live generation timestamps rendered at the top of each printed sheet.

