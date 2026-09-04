# Project Context & Session Memory

## Project: Next-Generation Modern E-Commerce Platform
**Last Updated:** September 4, 2026  
**Current Phase:** Phase 1 (Foundation & Architecture Setup)  
**Current Status:** Documentation & Architecture Suite Established; Ready for Code Implementation

---

## 1. Active Working Files Index

| File Path | Role / Content | Current Status |
| :--- | :--- | :--- |
| [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md) | Product Requirements Document: Features, Personas, NFRs, KPIs | Complete & Approved |
| [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md) | System Architecture: High-level flow, ERD, sequence diagrams, state machines | Complete & Approved |
| [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) | Tech stack, approved libraries, coding conventions, zero N+1 rules, security | Complete & Approved |
| [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md) | 10-Phase chronological implementation roadmap and task checklists | Complete & Approved |
| [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) | Design system: Poppins Google Font, Tailwind CSS v4 design tokens, UI specs | Updated |
| [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) | Tech stack: Tailwind CSS v4, Poppins font, zero-inline-CSS directives | Updated |
| [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) | Current working file index, session state, decisions, and immediate next steps | Active |
| [userview/templates/homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) | Modern luxury storefront homepage using pure Tailwind CSS & Poppins | Implemented |
| [userview/static/images/cartivo-horizontal.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-horizontal.png) | Horizontal header brand logo (Cartivo emblem + wordmark) | Active |
| [userview/static/images/cartivo-logo.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-logo.png) | Master full brand logo with tagline ("Shop Smarter. Live Better.") | Active |
| [userview/static/images/cartivo-icon.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-icon.png) | Standalone speed cart emblem | Active |
| [userview/static/images/favicon.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.png) | 192x192 high-resolution PNG favicon | Active |
| [userview/static/images/favicon.ico](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.ico) | Multi-size browser favicon ICO (16px, 32px, 48px, 64px) | Active |
| [userview/static/src/input.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/input.css) | Tailwind CSS v4 input file with `@theme` config (Poppins & brand tokens) | Configured |

| [userview/static/src/output.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/output.css) | Compiled Tailwind CSS production output stylesheet | Built (44KB) |
| [userview/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/urls.py) | Storefront user routes (Home root path routed to `home_view`) | Active |
| [userview/views.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/views.py) | `home_view` rendering `homepage.html` | Active |
| [ecom/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/urls.py) | Root URL routing including `userview.urls` | Active |
| [ecom/settings.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/settings.py) | Project settings with `userview.apps.UserviewConfig` registered in `INSTALLED_APPS` | Active |
| [ecom/package.json](file:///d:/django_project/E-Commerce/E-Commerce/ecom/package.json) | Node package config with `@tailwindcss/cli` and `dev` watch script | Active |

---

## 2. Core Architectural Decisions Locked In

1. **Custom User Model First:**
   - Must implement `CustomUser` in `apps/accounts` before running the very first database migration to prevent Django auth migration conflicts.
2. **Modular Service Layer Pattern:**
   - Views will stay thin; business logic (checkout math, cart sync, payments) lives exclusively in `apps/<domain>/services.py`.
   - Complex queries, filters, and aggregations live in `apps/<domain>/selectors.py`.
3. **Dual Cart Architecture:**
   - Guest cart stored in secure session.
   - User cart stored in database (`Cart` & `CartItem` models).
   - Unified `CartService.merge_session_cart_to_user()` automatically executed upon login.
4. **Concurrency & Inventory Protection:**
   - Database transactions wrapped in `transaction.atomic()`.
   - Stock deduction protected by row-level locking (`select_for_update()`).
5. **Design System & Styling:**
   - **Framework:** Tailwind CSS v4 via `@tailwindcss/cli`.
   - **Typography:** Google Fonts `'Poppins'` (`300, 400, 500, 600, 700, 800`).
   - **Directives:** Strictly pure Tailwind utility classes; zero internal `<style>` or inline styling.
   - **Iconography:** Lucide Icons via CDN (`unpkg.com/lucide@latest`).

---

## 3. Current Workspace Snapshot

- Root folder: `d:\django_project\E-Commerce\E-Commerce\`
- Django project folder: `d:\django_project\E-Commerce\E-Commerce\ecom\`
- Active Apps: `userview` (`ecom/userview/`)
- Active Front-end: Tailwind CSS v4 compiled to `ecom/userview/static/src/output.css`.
- Active Storefront View: `home_view` rendering `homepage.html`.
- Dev Server: Running on `ecom`.

---

## 4. Immediate Next Actionable Steps (Phase 1 Kickoff)

- [ ] **Step 1:** Reorganize `ecom/ecom/settings.py` into a modular package:
  - `ecom/ecom/settings/base.py`
  - `ecom/ecom/settings/development.py`
  - `ecom/ecom/settings/production.py`
- [ ] **Step 2:** Create `.env` and `.env.example` using `django-environ`.
- [ ] **Step 3:** Create `apps/` directory and configure Python path in `manage.py` & `settings/base.py`.
- [ ] **Step 4:** Generate the `apps/accounts` app and define the `CustomUser` model.
- [ ] **Step 5:** Point `AUTH_USER_MODEL = 'accounts.CustomUser'` in settings.
- [ ] **Step 6:** Run initial database migrations (`makemigrations accounts` -> `migrate`).

---

## 5. Working Directives & Protocol
- **Instruction-Driven Execution:** Strictly follow user instructions step-by-step; do not leap ahead unprompted.
- **Specification Compliance:** Align all code, models, views, and templates with [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md), [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md), [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md), [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md), and [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md).
- **Continuous Memory Sync:** Update [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) with active working files, completed steps, and state changes after every instructed modification.

---

## 6. Session Change Log
- **2026-09-04:**
  - Standardized and expanded [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md) with comprehensive feature specifications, user personas, NFRs, and success metrics.
  - Upgraded [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md) with Mermaid ERD, sequence diagrams for search, cart sync, checkout concurrency, and webhook processing.
  - Authored [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) defining libraries, zero N+1 rules, layered service pattern, and security standards.
  - Authored [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md) establishing a 10-phase milestone roadmap.
  - Authored [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) containing the full design token system, typography scale, and UI component specifications.
  - Initialized and updated [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) with working directives and current working file tracking protocol.
  - **Full Codebase Audit Completed:** Read and verified all documents and code files ([prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md), [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md), [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md), [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md), [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md), [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md), `manage.py`, `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `.gitignore`, and `README.md`).
  - **Userview App Creation & Wiring:**
    - Created `userview` app inside `ecom/`.
    - Registered `userview.apps.UserviewConfig` in `INSTALLED_APPS` inside [settings.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/settings.py).
    - Defined storefront route in [userview/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/urls.py).
    - Mounted `userview.urls` at root in [ecom/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/urls.py).
  - **Brand Identity & Logo Integration:**
    - Integrated uploaded **Cartivo** image ("Shop Smarter. Live Better.").
    - Generated multi-resolution [favicon.ico](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.ico) and [favicon.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.png) cropped and centered from the shopping cart speed emblem.
    - Generated [cartivo-horizontal.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-horizontal.png) tailored for header and footer navigation.
    - Updated [homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) with favicon links in `<head>`, brand logo in sticky navigation header, and footer brand block.
    - Updated [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) with Brand Identity & Logo Assets section.
  - **Tablet & Mobile Responsiveness + Skeleton Shimmer Animations:**
    - Configured `@keyframes shimmer` and `shimmer-effect` in [input.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/input.css) and recompiled to [output.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/output.css).
    - Updated [homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) with:
      - Responsive navigation with interactive slide-over mobile drawer navigation.
      - Mobile slide-down search bar.
      - Native app-style fixed bottom navigation bar on mobile devices (`md:hidden`).
      - Responsive grid adaptations across Mobile (2-col product grid), Tablet (3-col product grid, 2x2 categories), and Desktop (4-col grid).
      - Skeleton shimmer loading placeholders with smooth `opacity-0` to `opacity-100` image reveal on `onload`.
      - Text entrance animations (`animate-fade-in-up`) on hero and headline elements.
    - Documented Breakpoints and Shimmer animation specs in [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md).
    - Verified Django checks: 0 issues reported.






