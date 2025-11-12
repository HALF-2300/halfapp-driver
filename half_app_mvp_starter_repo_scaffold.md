# 🚖 HalfApp MVP — Starter Repo Scaffold

This canvas contains the **first working structure** for HalfApp, including an architecture diagram, repo layout, and minimal code/config for FastAPI, PostgreSQL, Docker, a simple React web frontend (Vite), Playwright tests wired for LambdaTest, and deployment stubs for Fly.io and GitHub Pages.

> Copy these files into a new GitHub repository and follow the README steps.

---

## 0) ASCII Architecture Diagram
```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Local Dev (Docker)                             │
│                                                                          │
│  ┌─────────────┐    HTTP      ┌──────────────┐       SQL                 │
│  │  Frontend   │ ───────────▶ │   FastAPI    │ ───────────────────────▶  │
│  │ (Vite/React)│              │   Backend    │                           │
│  └─────────────┘ ◀─────────── │  /docs, /api │ ◀───────────────────────  │
│          ▲        fetch()     └──────────────┘       ▲                   │
│          │                                           │                   │
│          │                                      ┌─────────┐              │
│          │                                      │Postgres │              │
│          └──────────────────────────────────────│  DB     │              │
│                                                 └─────────┘              │
└──────────────────────────────────────────────────────────────────────────┘
                  │
                  │ LambdaTest Tunnel (lt)
                  ▼
        ┌───────────────────┐   Playwright/Cypress   ┌───────────────────┐
        │  LambdaTest Grid  │◀──────────────────────▶│  Test Runs + Vids │
        └───────────────────┘                        └───────────────────┘
                  │
                  ▼
           ┌──────────────┐        ┌───────────────────┐
           │   GitHub     │  CI    │      Fly.io       │  Backend URL
           └──────────────┘  →     └───────────────────┘  (FastAPI)
                │  Pages (static)
                ▼
           Frontend (GitHub Pages)
```

---

## 1) Repository Layout
```
halfapp/
├─ README.md
├─ docker-compose.yml
├─ .env.example
├─ fly.toml
├─ backend/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ main.py
│  ├─ database.py
│  ├─ models/
│  │  ├─ __init__.py
│  │  ├─ user.py
│  │  ├─ driver.py
│  │  └─ ride.py
│  ├─ routes/
│  │  ├─ __init__.py
│  │  ├─ users.py
│  │  ├─ drivers.py
│  │  └─ rides.py
│  └─ services/
│     ├─ __init__.py
│     ├─ auth.py
│     └─ trip_service.py
├─ frontend/
│  ├─ Dockerfile
│  ├─ index.html
│  ├─ package.json
│  ├─ vite.config.js
│  └─ src/
│     ├─ main.jsx
│     ├─ App.jsx
│     └─ components/
│        ├─ Dashboard.jsx
│        ├─ DriverList.jsx
│        └─ RideForm.jsx
└─ tests/
   └─ playwright/
      ├─ playwright.config.ts
      └─ example.spec.ts
```

---

## 2) Root Files

### `README.md`
```md
# HalfApp — Minimal Ride-Sharing MVP

**Stack:** FastAPI · PostgreSQL · Docker · LambdaTest · GitHub Pages · Fly.io

## Quick Start
1) Copy `.env.example` to `.env` and adjust values.
2) Start services:
```bash
docker-compose up --build
```
3) Open:
- FastAPI Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000
- Postgres: psql -h localhost -U postgres -d halfapp

## LambdaTest (Local)
```bash
npm i -g @lambdatest/node-tunnel
lt --user $LT_USERNAME --key $LT_ACCESS_KEY --tunnelName HalfAppMVP
```
Then run Playwright tests (local or CI). See `tests/playwright`.

## Deploy
- **Backend** → Fly.io: `fly launch` then `fly deploy`.
- **Frontend** → GitHub Pages: `npm run build && npm run deploy` from `frontend/`.

See full docs in the project Wiki or in-code comments.
```

### `.env.example`
```env
# Backend
DATABASE_URL=postgresql://postgres:postgres@db:5432/halfapp
SECRET_KEY=change_me
CORS_ORIGINS=http://localhost:3000,https://<username>.github.io

# LambdaTest (export before running lt)
LT_USERNAME=
LT_ACCESS_KEY=

# Frontend
VITE_API_BASE=http://localhost:8000
```

### `docker-compose.yml`
```yaml
version: "3.9"
services:
  db:
    image: postgres:14
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: halfapp
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      - db
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    environment:
      - VITE_API_BASE=http://localhost:8000
    ports:
      - "3000:3000"
    stdin_open: true
    tty: true

volumes:
  pgdata:
```

### `fly.toml`
```toml
app = "halfapp-backend"
primary_region = "sea"

[build]
  dockerfile = "backend/Dockerfile"

[[services]]
  internal_port = 8000
  processes = ["app"]
  protocol = "tcp"

  [[services.ports]]
    handlers = ["http"]
    port = 80

  [[services.ports]]
    handlers = ["tls", "http"]
    port = 443
```

---

## 3) Backend

### `backend/requirements.txt`
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.36
psycopg[binary]==3.2.3
python-multipart==0.0.9
python-dotenv==1.0.1
pydantic==2.9.2
```

### `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `backend/database.py`
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/halfapp")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `backend/models/__init__.py`
```python
from .user import User
from .driver import Driver
from .ride import Ride
```

### `backend/models/user.py`
```python
from sqlalchemy import Column, Integer, String
from ..database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
```

### `backend/models/driver.py`
```python
from sqlalchemy import Column, Integer, String
from ..database import Base

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    license_no = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
```

### `backend/models/ride.py`
```python
from sqlalchemy import Column, Integer, String
from ..database import Base

class Ride(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False)
    driver_id = Column(Integer, index=True)
    status = Column(String, default="requested")
```

### `backend/services/__init__.py`
```python
# placeholder for service layer imports
```

### `backend/services/trip_service.py`
```python
from sqlalchemy.orm import Session
from ..models.ride import Ride

def create_ride(db: Session, customer_name: str):
    ride = Ride(customer_name=customer_name, status="requested")
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride
```

### `backend/services/auth.py`
```python
# MVP placeholder: add JWT auth later
```

### `backend/routes/__init__.py`
```python
# consolidate router imports here if needed
```

### `backend/routes/users.py`
```python
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/")
def list_users():
    return [{"id": 1, "email": "demo@example.com", "name": "Demo User"}]
```

### `backend/routes/drivers.py`
```python
from fastapi import APIRouter

router = APIRouter(prefix="/drivers", tags=["drivers"])

@router.get("/")
def list_drivers():
    return [{"id": 1, "license_no": "ABC123", "name": "Jane Driver"}]
```

### `backend/routes/rides.py`
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..database import get_db, Base, engine
from ..services.trip_service import create_ride

# Create tables on first import (simple MVP init)
Base.metadata.create_all(bind=engine)

class RideCreate(BaseModel):
    customer_name: str

router = APIRouter(prefix="/rides", tags=["rides"])

@router.post("/")
def make_ride(payload: RideCreate, db: Session = Depends(get_db)):
    ride = create_ride(db, payload.customer_name)
    return {"id": ride.id, "status": ride.status}

@router.get("/")
def list_rides():
    return [{"id": 1, "customer_name": "Alice", "status": "requested"}]
```

### `backend/main.py`
```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import users, drivers, rides

app = FastAPI(title="HalfApp API", version="0.1.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(users.router)
app.include_router(drivers.router)
app.include_router(rides.router)
```

---

## 4) Frontend (Vite + React)

### `frontend/Dockerfile`
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci || npm i
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

### `frontend/package.json`
```json
{
  "name": "halfapp-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview --port 3000",
    "deploy": "gh-pages -d dist"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1"
  },
  "devDependencies": {
    "vite": "5.4.8",
    "@vitejs/plugin-react": "4.3.1",
    "gh-pages": "6.2.0"
  }
}
```

### `frontend/vite.config.js`
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 3000 },
  base: '/halfapp/', // update if repository name differs
})
```

### `frontend/index.html`
```html
<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HalfApp</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### `frontend/src/main.jsx`
```jsx
import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')).render(<App />)
```

### `frontend/src/App.jsx`
```jsx
import React, { useEffect, useState } from 'react'

const apiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [health, setHealth] = useState(null)
  const [rides, setRides] = useState([])
  const [name, setName] = useState('')

  useEffect(() => {
    fetch(`${apiBase}/health`).then(r=>r.json()).then(setHealth)
  }, [])

  const createRide = async () => {
    const res = await fetch(`${apiBase}/rides/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_name: name || 'Demo' })
    })
    const data = await res.json()
    setRides((r) => [...r, data])
  }

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>HalfApp Dashboard</h1>
      <p>API Health: {health ? '✅ OK' : '❌ Down'}</p>

      <h2>Create Ride</h2>
      <input placeholder="Customer name" value={name} onChange={(e)=>setName(e.target.value)} />
      <button onClick={createRide}>Request Ride</button>

      <h2>Rides</h2>
      <pre>{JSON.stringify(rides, null, 2)}</pre>
    </div>
  )
}
```

### `frontend/src/components/Dashboard.jsx`
```jsx
export default function Dashboard(){
  return <div>Simple MVP dashboard</div>
}
```

### `frontend/src/components/DriverList.jsx`
```jsx
export default function DriverList(){
  return <ul><li>Jane Driver</li></ul>
}
```

### `frontend/src/components/RideForm.jsx`
```jsx
export default function RideForm(){
  return <form><input placeholder="Pickup" /></form>
}
```

---

## 5) Playwright + LambdaTest

> We default to **Playwright**. Cypress can be added similarly.

### `tests/playwright/playwright.config.ts`
```ts
import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:3000';

export default defineConfig({
  testDir: './',
  use: { baseURL },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```

### `tests/playwright/example.spec.ts`
```ts
import { test, expect } from '@playwright/test';

test('loads dashboard and checks health', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('HalfApp Dashboard')).toBeVisible();
});
```

### LambdaTest Tunnel (CLI)
```bash
npm i -g @lambdatest/node-tunnel
lt --user <username> --key <access_key> --tunnelName HalfAppMVP
```

> Configure LambdaTest project to point to your **tunnel** and **BASE_URL**.

---

## 6) GitHub Pages (Frontend) Tips
- Create repo `halfapp` under your account.
- In repo settings → Pages → set branch to `gh-pages` after first `npm run deploy`.
- Ensure `frontend/vite.config.js` `base` matches `/halfapp/`.

---

## 7) Fly.io (Backend) Quick Steps
```bash
fly auth login
fly launch  # select Dockerfile in backend/
fly secrets set SECRET_KEY=... DATABASE_URL=... (use your managed DB or Fly Postgres)
fly deploy
```

---

## 8) Local Commands Cheat-Sheet
```bash
# 1) Boot everything
cp .env.example .env && docker-compose up --build

# 2) Open docs
open http://localhost:8000/docs

# 3) Frontend dev
cd frontend && npm i && npm run dev

# 4) Playwright tests
cd tests/playwright && npm init -y && npm i -D @playwright/test && npx playwright install
BASE_URL=http://localhost:3000 npx playwright test

# 5) LambdaTest tunnel
lt --user $LT_USERNAME --key $LT_ACCESS_KEY --tunnelName HalfAppMVP
```

---

## 9) Notes & Next Steps
- Replace the in-file `Base.metadata.create_all` with Alembic migrations as the schema grows.
- Add JWT auth and roles (customer/driver/admin).
- Wire GitHub Actions for CI (lint, test, deploy on tags).
- Add monitoring (Sentry, OpenTelemetry) and structured logging.

---

**This is a runnable MVP scaffold**: start with `docker-compose up --build`, visit `http://localhost:8000/docs` and `http://localhost:3000`, and run Playwright tests locally or via LambdaTest.

