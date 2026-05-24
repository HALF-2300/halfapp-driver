# HalfApp staging infrastructure (Agent 1)

**Orchestration:** `docs/HALFAPP_STAGING_CLOSURE_ORCHESTRATION_01.md` · **Proof (fill after VPS):** `docs/STAGING_INFRA_PROOF_V0_1.md`

Operator runbook for a single Ubuntu 24.04 VPS running **API + OSRM + nginx**. PostgreSQL lives on **Neon** (external). OSRM graph prep is **Agent 2** (`docker/osrm-portland/` — do not change from this lane).

## Layout

```
infra/staging/
├── README.md                 # this file
├── docker-compose.yml        # api, osrm-routed, nginx
├── docker/Dockerfile.api     # API image build
├── nginx/halfapp.conf        # TLS, /api, /osrm, /sse
├── env/
│   ├── staging.env.template  # committed — all variables, no secrets
│   └── staging.env.local     # gitignored — fill on laptop + copy to VPS
├── scripts/
│   ├── 01_provision_vps.sh
│   ├── 02_deploy_api.sh
│   ├── 03_health_check.sh
│   └── 04_rotate_logs.sh
├── systemd/halfapp-api.service   # optional host-native API
└── checklist/OWNER_CAR_DAY.md
```

## Human gate: GATE-VPS-1

Provision a VPS (example: Hetzner `cx22`, Ubuntu 24.04):

```bash
hcloud server create --name halfapp-staging --type cx22 --image ubuntu-24.04 --ssh-key <key>
```

Record connection details in `infra/staging/env/staging.env.local` (local copy):

```bash
STAGING_HOST=<public-ip>
STAGING_USER=halfapp
STAGING_SSH_KEY=~/.ssh/id_ed25519
```

Copy the same file to the server as `/opt/halfapp-driver/infra/staging/env/staging.env.local` after the first clone (or `scp` before running provision).

## 1. Prepare secrets (before touching the VPS)

```bash
cp infra/staging/env/staging.env.template infra/staging/env/staging.env.local
```

Fill at minimum:

| Variable | Notes |
|----------|--------|
| `DATABASE_URL` | Neon PostgreSQL URL with `sslmode=require` |
| `SECRET_KEY` | ≥32 random bytes (`HALFAPP_ENV=production`) |
| `CORS_ORIGINS` | `https://staging.halfapp.app,https://rider-stub.halfapp.app` |

Commit **only** `staging.env.template`, never `staging.env.local`.

## 2. DNS

Point `staging.halfapp.app` A/AAAA record to the VPS public IP.

## 3. Provision the VPS (idempotent)

On the server as **root**:

```bash
export HALFAPP_REPO_URL='https://github.com/YOUR_ORG/halfapp-driver.git'  # if needed
bash /opt/halfapp-driver/infra/staging/scripts/01_provision_vps.sh
```

Or from your laptop after copying `staging.env.local` to the host:

```bash
scp -i ~/.ssh/id_ed25519 infra/staging/env/staging.env.local halfapp@$STAGING_HOST:/tmp/
ssh -i ~/.ssh/id_ed25519 root@$STAGING_HOST 'mkdir -p /opt/halfapp-driver/infra/staging/env && mv /tmp/staging.env.local /opt/halfapp-driver/infra/staging/env/'
ssh -i ~/.ssh/id_ed25519 root@$STAGING_HOST 'git clone ... /opt/halfapp-driver && bash /opt/halfapp-driver/infra/staging/scripts/01_provision_vps.sh'
```

The script links `staging.env.local` → `/etc/halfapp/staging.env` and **exits with a clear error** if the local env file is missing.

## 4. TLS (Let’s Encrypt)

Create Docker volumes (first time only):

```bash
docker volume create halfapp-staging-letsencrypt
docker volume create halfapp-staging-certbot-www
```

With nginx serving HTTP (ACME webroot in `halfapp.conf`):

```bash
cd /opt/halfapp-driver
docker compose -f infra/staging/docker-compose.yml up -d nginx   # may warn until certs exist
# After port 80 is reachable:
docker run --rm \
  -v halfapp-staging-certbot-www:/var/www/certbot \
  -v halfapp-staging-letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d staging.halfapp.app --email ops@halfapp.app --agree-tos --no-eff-email
docker compose -f infra/staging/docker-compose.yml restart nginx
```

Until certificates exist, the HTTPS `server` block will not load; use HTTP health at `http://staging.halfapp.app/health` for bootstrap.

## 5. OSRM data (Agent 2)

Prepared files live under `docker/osrm-portland/data/*.osrm`. Set `OSRM_DATA_DIR` in `staging.env.local` if using a non-default path.

Start OSRM (optional before API if data is ready):

```bash
docker compose -f infra/staging/docker-compose.yml up -d osrm-routed
```

**API deploy does not require OSRM data** — `02_deploy_api.sh` prints a warning and continues.

## 6. Deploy API

As user `halfapp`:

```bash
cd /opt/halfapp-driver
chmod +x infra/staging/scripts/*.sh
bash infra/staging/scripts/02_deploy_api.sh
```

This pulls `main`, builds `api`, runs `alembic upgrade head`, restarts the API container, runs `03_health_check.sh`, and tails logs.

Ensure **nginx** is up before the health check uses `https://staging.halfapp.app`:

```bash
docker compose -f infra/staging/docker-compose.yml up -d
```

## 7. Health checks

```bash
BASE=https://staging.halfapp.app bash infra/staging/scripts/03_health_check.sh
```

Exits non-zero if API health, version, OSRM route, or CORS preflight fails.

Local API-only smoke (nginx bypass):

```bash
curl -fsS http://127.0.0.1:8000/health | jq .
```

## 8. Log rotation

```bash
sudo bash infra/staging/scripts/04_rotate_logs.sh
# Optional cron: 0 3 * * * root /opt/halfapp-driver/infra/staging/scripts/04_rotate_logs.sh
```

## Validate compose file (laptop or CI)

From repo root:

```bash
docker compose -f infra/staging/docker-compose.yml config
```

For local builds without `/etc/halfapp/staging.env`:

```bash
export HALFAPP_STAGING_ENV_FILE=infra/staging/env/staging.env.local
docker compose -f infra/staging/docker-compose.yml config
```

## Optional: host systemd API

If you run uvicorn on the host instead of the `api` container, use `systemd/halfapp-api.service` and **stop** the compose `api` service to avoid port 8000 conflicts.

## Owner-car day

See `checklist/OWNER_CAR_DAY.md`.

## Unblocks after GATE-VPS-1

- **Agent 2** — OSRM graph build and runtime proof (`docker/osrm-portland/`)
- **Agent 3** — driver/rider app staging URLs and JWT flows
