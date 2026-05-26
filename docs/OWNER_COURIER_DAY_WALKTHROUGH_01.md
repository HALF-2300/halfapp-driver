# Owner Courier Day — Step-by-Step Walkthrough

**Companion to:** `docs/OWNER_COURIER_DAY_REPORT_01.md` (sign-off template) and `docs/OWNER_INTERNAL_TEST_RUNBOOK_01.md` (setup steps).  
**Purpose:** Concrete script the owner follows during the manual G3 walkthrough.  
**Posture:** internal-test mode. Payments are simulated. No real money. No public-launch claim.

---

## How to use this doc

1. Open four terminals (or browser tabs) and start the stack per §1.
2. Walk through §2–§7 in order. At each step, check the **Verify** boxes.
3. If a verify fails, **stop** and record the failure in the sign-off template (`OWNER_COURIER_DAY_REPORT_01`). Do not patch around it.
4. After §7, fill in the sign-off block in the report template and commit the result.

---

## 1. Pre-flight

| # | Check | Command / where |
|---|-------|-----------------|
| 1.1 | Ports 8000, 3022, 3023, 3024 free | `netstat -ano \| findstr ":8000 :3022 :3023 :3024"` (none should be in use by another app) |
| 1.2 | Python 3.11, Node 18+ | `py -3.11 --version` · `node -v` |
| 1.3 | Repo clean | `git status` (working tree clean or only intended local edits) |
| 1.4 | Backend SQLite db reset (optional fresh start) | delete `backend/halfapp_local.db` then `cd backend && py -3.11 -m alembic upgrade head` |

**Verify:**
- ☐ All four ports free
- ☐ Toolchain present
- ☐ Backend migrates clean (output ends at `0036_driver_readiness_fields`)

---

## 2. Start the stack

Terminal 1 — backend:

```powershell
cd c:\Users\him\Desktop\halfapp-driver\backend
py -3.11 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Terminal 2 — driver-app:

```powershell
cd c:\Users\him\Desktop\halfapp-driver\driver-app
npm run dev -- --port 3022
```

Terminal 3 — rider-app:

```powershell
cd c:\Users\him\Desktop\halfapp-driver\rider-app
npm run dev -- --port 3023
```

Terminal 4 (optional) — ops-app:

```powershell
cd c:\Users\him\Desktop\halfapp-driver\ops-app
npm run dev -- --port 3024
```

**Verify:**
- ☐ `http://127.0.0.1:8000/health` → `{"status":"ok","service":"halfapp-backend"}`
- ☐ `http://127.0.0.1:3022` → driver portal / login page renders
- ☐ `http://127.0.0.1:3023` → rider sign-in page renders
- ☐ `http://127.0.0.1:3024` → ops sign-in page renders (if running)

---

## 3. Register accounts

### 3a. Driver (in driver-app)

1. Click **Create account** tab.
2. Fill: name (e.g. `Owner Courier`), license number (any unique string), email, password (≥ 6 chars).
3. Submit.
4. After registration the driver is **pending approval**. Approve via API:

```powershell
$BASE = "http://127.0.0.1:8000"
# Get the driver id from the registration response or:
Invoke-RestMethod -Uri "$BASE/drivers/me" -Headers @{ Authorization = "Bearer <driver_token>" }
# Then approve via admin endpoint (requires admin token / dev-mode flag).
```

(For local-dev convenience the runbook may include a one-shot helper. If unsure, use the admin approval flow in `routes/admin_driver_approval.py`.)

### 3b. Rider (in rider-app)

1. Click **Create account**.
2. Fill name, **different email from driver**, password.
3. Submit.

### 3c. Ops (in ops-app, if used)

1. Sign in with an admin account (see `backend/scripts/owner_runbook_verify.py` for a programmatic helper to seed one).

**Verify:**
- ☐ Driver shows `Approved` in the driver Profile screen
- ☐ Rider lands on home screen with **Get a ride** panel
- ☐ Ops can see the empty Rides table

---

## 4. Rider requests a delivery / ride

In **rider-app** (terminal 3, browser):

1. On the Home screen, enter a pickup address (any landmark recognized by the local stub geocoder, e.g. `Pioneer Courthouse Square, Portland`).
2. Enter a dropoff address (e.g. `Portland Airport`).
3. Click **Confirm addresses**.
4. Wait for the **Estimated fare** chip to appear.
5. Confirm the payment label reads **Test record · no charge** (not "Ledger (beta)" — that copy was retired on 2026-05-25).
6. Click **Request ride**.

**Verify:**
- ☐ Status banner switches to **Finding your driver…**
- ☐ URL changes to `/#/ride/<id>`
- ☐ Pulse animation visible (blue)
- ☐ Cancel button available
- ☐ Page does NOT crash; no console errors

---

## 5. Driver accepts and runs the lifecycle

In **driver-app** (terminal 2, browser):

1. From the cockpit, tap **Go online**. State badge changes to **Online**.
2. The incoming-job sheet should appear within a few seconds.
3. Confirm the eyebrow reads **Incoming job · open board**.
4. Tap **Accept**.

**Verify (accept):**
- ☐ State badge: **To pickup**
- ☐ Sheet shows `sheet-accepted_to_pickup`
- ☐ Rider-app status changes to **Driver matched** (with driver card)

Continue lifecycle:

5. Tap **Advance to pickup** (the `advance-accepted_to_pickup` button).
6. Tap **Arrived at pickup** (`advance-arrived_pickup`).
7. Tap **Start trip** (`advance-in_progress`).

**Verify each step:**
- ☐ Driver badge updates: To pickup → At pickup → In progress
- ☐ Rider banner updates correspondingly (En route / Arrived / In progress)
- ☐ Each transition is visible on the **ops console** Rides table (refresh or wait 5s for poll)

8. Tap the final advance to **Complete**.

**Verify (complete):**
- ☐ Driver: **Completed flash** appears, badge returns to **Online**
- ☐ Rider: receipt screen renders with fare total and **Book another ride** button
- ☐ Receipt label reflects that this is a calculation record (no payout claim)

---

## 6. Inspection

### 6a. Driver-side

1. Tap **Trips** tab. The completed job is at the top.
2. Click into the job → audit receipt opens.
3. Confirm:
   - ☐ Title: **Trip audit**
   - ☐ Section labelled **Job** with **Job ID** row
   - ☐ Pricing breakdown shows `financial_locked: Yes`
   - ☐ Obligation copy present (no "paid out" claim)
4. Tap **Earnings** tab. Total reflects this trip; **Recent deliveries** shows the row.

### 6b. Rider-side

1. Tap **Account** → confirm rider ID, email shown.
2. Tap **Help** → confirm FAQ entries render (cancel, fare reality, ETA source, emergency).
3. Return Home → confirm the completed ride is in **Recent trips**.

### 6c. Ops-side (if running)

1. Open Rides table.
2. Locate the trip; confirm:
   - ☐ Status badge: `completed`
   - ☐ Payment column shows the simulated payment status (if Phase 3 enabled)
   - ☐ Click the trip ID → detail page shows assign + cancel are disabled (terminal state)
3. Open Drivers table.
4. Locate the courier; confirm:
   - ☐ Online: Yes
   - ☐ Approval: approved
   - ☐ Active ride: `—` (no active job after completion)
   - ☐ Presence state: available or offline (depends on whether you went offline)

---

## 7. Failure-mode drills (optional but recommended)

Run any/all of these to prove honest behavior under stress.

### 7a. Refresh mid-trip

1. Start a fresh trip and advance to **In progress**.
2. Hit `F5` to hard-refresh the cockpit.
3. ☐ Verify the blue **Resumed active ride #N (in_progress)** banner appears
4. ☐ Verify the in-progress sheet is restored with the same ride ID

### 7b. Decline an offer

1. Bring the driver online with a new incoming job.
2. Tap **Hide for this driver**.
3. ☐ Verify backend-hide-notice appears
4. ☐ Verify the same job does NOT reappear after a marketplace sync

### 7c. Race / claim conflict (multi-driver)

(Requires a second driver browser session — Edge or incognito Chrome works.)

1. Register and approve a second driver. Bring both online.
2. Submit a new ride from rider-app.
3. Both drivers see the offer. Race-click **Accept** on each.
4. ☐ Verify exactly one wins; the other sees **Job already claimed**

### 7d. Stale presence

1. While online, stop the backend (Ctrl+C terminal 1).
2. Wait > 45 seconds.
3. Restart backend.
4. ☐ Verify the orange **You may appear offline to dispatch** banner appeared during the outage, and clears after recovery.

---

## 8. After the walkthrough

1. Fill in the sign-off block in `docs/OWNER_COURIER_DAY_REPORT_01.md`:
   - Date (UTC)
   - Owner name
   - Environment (local / staging)
   - Database (sqlite / postgresql)
   - Verdict: **GO_OWNER_COURIER_DAY** or **NO_GO** with reason
2. Commit the filled-in report on a local branch (no push needed).
3. If verdict is GO, update `docs/CURRENT_TRUTH.md` G3 row from **PENDING_OWNER** to **GO** with the date and report reference.

---

## Truth boundary (unchanged)

This walkthrough proves the **local internal product loop**. It does **not** prove:

- Real payment processing
- Real road-network routing (until G2 OSRM proof is GO)
- Production hosting
- Legal operation in any jurisdiction
- Mobile app-store readiness
- Real driver onboarding (background check, insurance)

Verdict scope: **INTERNAL_PRODUCT_COMPLETION_GO** stays; **PUBLIC_LAUNCH_NO_GO** stays.

Use the checks above only to prove the local stack actually walks the end-to-end flow without fakes or hand-waving.
