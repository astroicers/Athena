FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    hashcat && rm -rf /var/lib/apt/lists/*

# Download rockyou.txt wordlist
RUN mkdir -p /usr/share/wordlists && \
    curl -sL https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt \
    -o /usr/share/wordlists/rockyou.txt || true

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
