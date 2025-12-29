"""
Peptide AI - FastAPI Application

Main entry point for the API layer.
MINIMAL VERSION FOR DEBUGGING
"""
print("DEBUG: Starting minimal main.py", flush=True)

from fastapi import FastAPI
from datetime import datetime

print("DEBUG: FastAPI imported", flush=True)

# Create minimal app without lifespan or any other dependencies
app = FastAPI(
    title="Peptide AI",
    version="0.1.0",
)

print("DEBUG: App created", flush=True)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"status": "ok", "version": "minimal-debug"}


@app.get("/health")
async def health():
    """Health endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


print("DEBUG: Routes defined, app ready", flush=True)
