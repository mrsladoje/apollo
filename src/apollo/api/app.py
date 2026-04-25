"""Apollo FastAPI application — main entry point (PLAN-C §5.1)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apollo.api.routes import chat, sim, whatif

app = FastAPI(title="Apollo Digital Co-Pilot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(sim.router)
app.include_router(whatif.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
