# Example Athena MCP tool container (FastMCP, streamable-http). Placeholder skeleton — replace
# server.py with real logic and pin dependencies before publishing a real tool.
FROM python:3.12-slim

WORKDIR /app
COPY server.py .

RUN pip install --no-cache-dir fastmcp

EXPOSE 8080
CMD ["python", "server.py"]
