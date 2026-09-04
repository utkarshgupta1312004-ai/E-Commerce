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
| [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) | Design system: Color tokens, typography scale, component specs, micro-interactions | Complete & Approved |
| [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) | Current working file index, session state, decisions, and immediate next steps | Active |

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
   - Vanilla CSS custom properties (`--color-brand-primary`, etc.) defined in `design.md`.
   - Lightweight Alpine.js for micro-interactions; zero heavy bloated CSS libraries.

---

## 3. Current Workspace Snapshot

- Root folder: `d:\django_project\E-Commerce\E-Commerce\`
- Existing Django scaffold: Located in `ecom/` (`manage.py`, default `ecom/settings.py`, `ecom/urls.py`).
- Virtual Environment: `venv/` exists in workspace root.
- Database: Not yet initialized with tables (waiting for Custom User model setup).

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
- [ ] **Step 7:** Create base templates (`templates/base.html`) and design system CSS (`static/css/main.css`).

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

