FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc git libffi-dev libssl-dev libxml2-dev libxslt1-dev \
    libldap2-dev libsasl2-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir . \
    && pip install --no-cache-dir "git+https://github.com/Pennyw0rth/NetExec@main"

COPY . .

CMD ["python", "-m", "server"]
