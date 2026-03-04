FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# MCP servers run as stdio by default; for HTTP mode:
# CMD ["python", "-m", "server", "--transport", "streamable-http", "--port", "8080"]
CMD ["python", "-m", "server"]
