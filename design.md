# Design System & UI Styleguide

## Project: Next-Generation Modern E-Commerce Platform

---

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
- **Primary Body Font:** `'Plus Jakarta Sans'`, `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Headings & Display:** `'Outfit'`, `'Plus Jakarta Sans', sans-serif`
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

### 5.4. Slide-Over Cart Drawer
- Width: `420px` (or `100vw` on mobile).
- Slide-in from right with dark backdrop overlay (`rgba(15, 23, 42, 0.4)`).
- Header with item count, scrollable list of items with thumbnail + quantity picker, sticky footer with subtotal, tax note, and primary "Checkout" button.
