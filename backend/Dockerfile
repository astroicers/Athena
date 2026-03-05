FROM python:3.12-slim

LABEL org.opencontainers.image.title="Athena Backend" \
      org.opencontainers.image.description="AI-driven C5ISR cyber operations command platform" \
      org.opencontainers.image.url="https://github.com/astroicers/Athena" \
      org.opencontainers.image.source="https://github.com/astroicers/Athena" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="0.1.0"

WORKDIR /app

# Install system dependencies (nmap required by python-nmap wrapper)
RUN apt-get update && apt-get install -y --no-install-recommends nmap curl && rm -rf /var/lib/apt/lists/*

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
    CMD curl -sf http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
