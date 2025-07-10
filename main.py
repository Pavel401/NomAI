import json
from typing import Any, Dict
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import nutrition
from app.api.endpoints import chat
from app.services.chat_database import Database
from app.utils.envManager import get_env_variable, get_env_variable_safe
from app.middleware.exception_handlers import setup_exception_handlers
import logfire


# Configure logfire for chat functionality
logfire.configure(send_to_logfire="if-token-present")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Initialize chat database connection
    async with Database.connect() as db:
        # Store database instance in app state
        app.state.chat_db = db
        yield
        # Cleanup happens automatically when context exits


# Safely get environment variables
isProd = get_env_variable_safe("PROD", "false").lower() == "true"

# Create FastAPI app
app = FastAPI(
    title="NomAI Nutrition API",
    description="AI-powered nutrition analysis API with chat functionality",
    version="1.0.0",
    debug=not isProd,
    lifespan=lifespan,
)

# Setup global exception handlers
app = setup_exception_handlers(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(nutrition.router, prefix="/nutrition")
app.include_router(chat.router, prefix="/chat")


if __name__ == "__main__":
    host = get_env_variable_safe("HOST", "0.0.0.0")
    port = int(get_env_variable_safe("PORT", "8000"))

    uvicorn.run(
        app, host=host, port=port, reload=not isProd  # Enable reload in development
    )
