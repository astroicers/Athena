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

# Enable OpenSSL 3 legacy provider for pywinrm NTLM (MD4 needed for NTLMv2)
RUN printf '%s\n' \
    'openssl_conf = openssl_init' \
    '[openssl_init]' \
    'providers = provider_sect' \
    '[provider_sect]' \
    'default = default_sect' \
    'legacy = legacy_sect' \
    '[default_sect]' \
    'activate = 1' \
    '[legacy_sect]' \
    'activate = 1' \
    > /etc/ssl/openssl-legacy.cnf
ENV OPENSSL_CONF=/etc/ssl/openssl-legacy.cnf

# Copy dependency specifications first for better Docker cache
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir .

# Copy application source code
COPY app/ app/
COPY alembic/ alembic/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop"]
