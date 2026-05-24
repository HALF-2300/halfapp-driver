# Legacy Frontend — Inactive / Archive

**Status:** Legacy. **Not** part of the active HalfApp / Liánlù product.

Date: 2026-05-20  
Order: `HALFAPP_STAGE0_TRUTH_BOUNDARY_LOCK_01`

---

## Do not use this directory as product evidence

This `frontend/` tree is a **historical multi-role** React app (driver, customer/rider, admin, stability tooling). It is **not** the active driver cockpit.

The active driver UI is only:

- `driver-app/`

The active API is only what `backend/main.py` mounts. See `docs/DORMANT_ROUTERS_INVENTORY.md`.

---

## Why this frontend is inactive

1. **Not wired to the active backend** — It expects routes such as `/admin/*` and legacy `/rides/*` handlers that are **not** registered by `backend/main.py`.
2. **No maintained package manifest in tree** — There is no `frontend/package.json` in the current workspace layout; do not assume `npm run build` works here without an explicit revival order.
3. **Misleading demos** — Admin dashboards and rider flows in this tree can look production-ready while returning 404 against the live API.

---

## Must not be revived without a separate migration order

Do **not** revive, mount, or market this frontend unless a dedicated order requires it and delivers:

- `package.json` and CI build for `frontend/`
- Matching mounted routers in `backend/main.py` with RBAC and tests
- Updated `docs/CURRENT_TRUTH.md` and `docs/PRODUCT_BOUNDARY_STAGE0.md`
- Removal of forbidden claims until each capability is actually implemented

Until then, treat all files here as **archive/reference only**.

---

## Where to work instead

| Need | Go to |
|------|--------|
| Driver UI | `driver-app/` |
| API truth | `backend/` + `docs/CURRENT_TRUTH.md` |
| Product boundary | `docs/PRODUCT_BOUNDARY_STAGE0.md` |
