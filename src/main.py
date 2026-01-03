"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.decisions import router as decisions_router
from src.models.database import init_db

# Initialize database
init_db()

app = FastAPI(
    title="Second Guess",
    description="Decision Quality Measurement System",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(decisions_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Second Guess",
        "version": "0.1.0",
        "description": "Decision Quality Measurement System"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
