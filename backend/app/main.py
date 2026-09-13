import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_quotes, routes_shipments, routes_reference, routes_dashboard

app = FastAPI(title="Tranable Logistics Platform API", version="0.1.0")

# CORS: localhost for local dev, plus any origins from FRONTEND_ORIGINS (comma-separated),
# used to allow the deployed frontend's public URL in hosted environments.
_extra_origins = [o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_quotes.router)
app.include_router(routes_shipments.router)
app.include_router(routes_reference.router)
app.include_router(routes_dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
