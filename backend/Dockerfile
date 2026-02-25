FROM python:3.11-slim

WORKDIR /app

# Copy dependency specifications first for better Docker cache
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Copy application source code
COPY app/ app/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health')" || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
