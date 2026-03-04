FROM python:3.11-slim

# nmap binary is required for python-nmap
RUN apt-get update && apt-get install -y --no-install-recommends nmap && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# MCP servers run as stdio by default; for HTTP mode:
# CMD ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
CMD ["python", "-m", "server"]
