# Peptide AI - Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Default port (Railway will override via PORT env var)
ENV PORT=8000
EXPOSE $PORT

# Run the application (use shell form to expand $PORT)
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
