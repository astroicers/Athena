FROM python:3.12-slim

# Install runtime dependencies for fetching/extracting the ffuf binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install ffuf from ffuf/ffuf GitHub releases (release-asset tarball pattern)
RUN FFUF_VERSION=$(wget -qO- https://api.github.com/repos/ffuf/ffuf/releases/latest \
        | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/') \
    && wget -q "https://github.com/ffuf/ffuf/releases/download/v${FFUF_VERSION}/ffuf_${FFUF_VERSION}_linux_amd64.tar.gz" \
       -O /tmp/ffuf.tar.gz \
    && tar -xzf /tmp/ffuf.tar.gz -C /tmp ffuf \
    && mv /tmp/ffuf /usr/local/bin/ffuf \
    && chmod +x /usr/local/bin/ffuf \
    && rm /tmp/ffuf.tar.gz

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bundle the default API path wordlist and the server
COPY wordlist.txt /app/wordlist.txt
COPY server.py .

EXPOSE 9105

CMD ["python", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9105"]
