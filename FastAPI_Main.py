"""
main.py
───────
Agrithm FastAPI application entry point.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api.routes import price, advisory, voice, webhook


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌾 Agrithm API starting up...")
    yield
    logger.info("Agrithm API shutting down.")


app = FastAPI(
    title="Agrithm API",
    description="AI-powered agricultural intelligence for Indian farmers",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(price.router,    prefix="/api/price",    tags=["Price Intelligence"])
app.include_router(advisory.router, prefix="/api/advisory", tags=["Advisory"])
app.include_router(voice.router,    prefix="/api/voice",    tags=["Voice Pipeline"])
app.include_router(webhook.router,  prefix="/webhook",      tags=["Webhooks"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "service": "Agrithm API", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true",
        log_level="info",
    )
