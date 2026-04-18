FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev git && \
    rm -rf /var/lib/apt/lists/*

# Clone Responder
RUN git clone --depth 1 https://github.com/lgandx/Responder.git /opt/Responder

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
