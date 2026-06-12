"""
FastAPI application entry point.

Creates the ASGI app, includes authentication router,
adds CORS middleware for React frontend, and defines health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.limiter import limiter
from app.routes import auth, simulations, players, schedule

app = FastAPI(
    title="Baseball Simulator API",
    description="Authentication backend for Monte Carlo baseball simulations",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS – allow React frontend to send cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URL,
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(simulations.router)
app.include_router(players.router)
app.include_router(schedule.router)


@app.get("/health")
async def health_check():
    """Simple health check endpoint to verify API is running."""
    return {"status": "ok", "message": "Auth backend is running"}
