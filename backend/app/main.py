"""
FastAPI application entry point.

Creates the ASGI app, includes authentication router,
adds CORS middleware for React frontend, and defines health check.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, simulations

app = FastAPI(
    title="Baseball Simulator API",
    description="Authentication backend for Monte Carlo baseball simulations",
    version="0.1.0",
)

# CORS – allow React frontend to send cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your React dev server
    allow_credentials=True,  # Required for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(simulations.router)


@app.get("/health")
async def health_check():
    """Simple health check endpoint to verify API is running."""
    return {"status": "ok", "message": "Auth backend is running"}
