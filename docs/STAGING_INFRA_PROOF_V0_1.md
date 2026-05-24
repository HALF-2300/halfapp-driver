# Staging Infra Proof v0.1 (Agent 1)

**Document ID:** `STAGING_INFRA_PROOF_V0_1`  
**Date:** 2026-05-24  
**Verdict:** **NO_GO** — blocked on `[HUMAN GATE] GATE-VPS-1`

---

## Preconditions

| Item | Status |
|------|--------|
| `infra/staging/scripts/provision-hetzner.sh` | Present |
| `infra/staging/scripts/01_provision_vps.sh` | Present |
| `infra/staging/staging.env.local.example` | Present |
| `infra/staging/nginx/halfapp-staging.conf` | Present |
| VPS provisioned | **Pending human** |
| `ssh staging docker ps` | **Not run** |

---

## Commands (run after GATE-VPS-1)

```bash
# 1. Provision (Hetzner)
export HCLOUD_TOKEN="<redacted>"
bash infra/staging/scripts/provision-hetzner.sh

# 2. Acceptance
source infra/staging/staging.env
ssh -i ~/.ssh/halfapp_staging_ed25519 "$VPS_USER@$VPS_IP" docker ps

# 3. Full verify script
bash infra/staging/scripts/verify-staging.sh
```

### Expected output (paste literal output here after run)

```
(paste docker ps + STAGING_ACCEPTANCE_OK)
```

---

## Nginx health (optional GATE-DNS-1)

```bash
curl -s "http://$VPS_IP/health"
# expect: ok
```

---

## Files changed (Agent 1 artifacts)

- `infra/staging/README.md`
- `infra/staging/env/staging.env.template`
- `infra/staging/docker-compose.yml`
- `infra/staging/scripts/02_deploy_api.sh`
- `infra/staging/scripts/03_health_check.sh`
- `infra/staging/scripts/01_provision_vps.sh`
- `infra/staging/scripts/provision-hetzner.sh`
- `infra/staging/scripts/verify-staging.sh`
- `infra/staging/nginx/halfapp-staging.conf`
- `infra/staging/docker-compose.yml`

---

## Agent report

**Blocked on GATE-VPS-1** — paste `VPS_IP` into `infra/staging/staging.env.local` and re-run verify script; then change verdict to **GO** and update `docs/CURRENT_TRUTH.md`.
