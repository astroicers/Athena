FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip && \
    rm -rf /var/lib/apt/lists/*

RUN FFUF_URL=$(wget -qO- "https://api.github.com/repos/ffuf/ffuf/releases/latest" \
      | grep -oP '"browser_download_url":\s*"\K[^"]*linux_amd64\.tar\.gz') && \
    wget -qO /tmp/ffuf.tar.gz "$FFUF_URL" && \
    tar -xzf /tmp/ffuf.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffuf && \
    rm -f /tmp/ffuf.tar.gz

RUN mkdir -p /opt/wordlists && \
    wget -qO /opt/wordlists/api-common.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints.txt" && \
    wget -qO /opt/wordlists/api-large.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints-res.txt"

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
