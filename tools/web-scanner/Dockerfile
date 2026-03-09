FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip && \
    rm -rf /var/lib/apt/lists/*

# httpx-toolkit
RUN HTTPX_URL=$(wget -qO- "https://api.github.com/repos/projectdiscovery/httpx/releases/latest" \
      | grep -oP '"browser_download_url":\s*"\K[^"]*linux_amd64\.zip') && \
    wget -qO /tmp/httpx.zip "$HTTPX_URL" && \
    unzip -o /tmp/httpx.zip -d /tmp/httpx-extract && \
    mv /tmp/httpx-extract/httpx /usr/local/bin/httpx && \
    chmod +x /usr/local/bin/httpx && \
    rm -rf /tmp/httpx.zip /tmp/httpx-extract

# nuclei
RUN NUCLEI_URL=$(wget -qO- "https://api.github.com/repos/projectdiscovery/nuclei/releases/latest" \
      | grep -oP '"browser_download_url":\s*"\K[^"]*linux_amd64\.zip') && \
    wget -qO /tmp/nuclei.zip "$NUCLEI_URL" && \
    unzip -o /tmp/nuclei.zip -d /tmp/nuclei-extract && \
    mv /tmp/nuclei-extract/nuclei /usr/local/bin/nuclei && \
    chmod +x /usr/local/bin/nuclei && \
    rm -rf /tmp/nuclei.zip /tmp/nuclei-extract

# nuclei templates
RUN nuclei -update-templates -ud /opt/nuclei-templates

# SecLists wordlists
RUN mkdir -p /opt/wordlists && \
    wget -qO /opt/wordlists/common.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" && \
    wget -qO /opt/wordlists/small.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-small.txt" && \
    wget -qO /opt/wordlists/large.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt"

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
