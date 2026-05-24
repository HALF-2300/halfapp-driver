# HalfApp Deployment Environment Variables

To run the HalfApp backend in a production or live-demo environment, the following environment variables are strictly enforced to prevent dev-mode security leaks.

## Required for Production

*   `HALFAPP_ENV`: Set to `production` to engage security guards.
*   `SECRET_KEY`: Must be a unique cryptographic string of **at least 32 characters**. Known unsafe values (`change_me`, `dev`, repository default, empty) **fail startup**.
    *   *Generation tip:* `python -c "import secrets; print(secrets.token_urlsafe(32))"`
*   `CORS_ORIGINS`: Comma-separated allowed frontend origins. **Required in production** — localhost is not auto-added. Wildcard `*` is rejected.
    *   *Example:* `https://driver.halfapp.demo,https://app.halfapp.com`
*   `HALFAPP_ENABLE_RIDE_SIMULATION`: **Omit or unset in production.** When unset, `POST /drivers/simulate-ride` returns `403` with `SIMULATION_DISABLED`.

## Test / CI

*   `HALFAPP_ENV=test` for pytest and Playwright backend processes.
*   `SECRET_KEY` must be a non-default test value (≥16 characters).
*   `HALFAPP_ENABLE_RIDE_SIMULATION=1` when tests call `/drivers/simulate-ride`.

## Development Mode (Default)

If `HALFAPP_ENV` is absent or set to `development`, the backend allows the repository dev default `SECRET_KEY` and unions CORS with `localhost:5173`, `localhost:3000`, and Playwright ports `3020–3034`.

Simulation still requires **`HALFAPP_ENABLE_RIDE_SIMULATION=1`** even in development (aligns driver UI flag with backend truth).

See also: `docs/HALFAPP_TOKEN_POLICY_SKETCH_01.md`, `docs/HALFAPP_PRODUCTION_GUARDS_SECRET_SIMULATION_CORS_01.md`.
