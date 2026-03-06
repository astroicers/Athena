FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip && \
    rm -rf /var/lib/apt/lists/*

RUN wget -qO /tmp/ffuf.tar.gz \
    "https://github.com/ffuf/ffuf/releases/latest/download/ffuf_$(uname -s)_$(uname -m).tar.gz" && \
    tar -xzf /tmp/ffuf.tar.gz -C /usr/local/bin/ ffuf && \
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
