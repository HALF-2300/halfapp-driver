import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import users, drivers, rides
from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.admin_access import router as admin_access_router
from database import engine, Base
from models import user, driver, ride  # Import all models to register them

# Create all tables
Base.metadata.create_all(bind=engine)

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

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(admin_access_router)
app.include_router(users.router)
app.include_router(drivers.router)
app.include_router(rides.router)