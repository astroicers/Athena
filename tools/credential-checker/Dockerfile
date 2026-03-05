FROM athena-mcp-base:latest

# Install xfreerdp3 for RDP auth-only checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    freerdp3-x11 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
