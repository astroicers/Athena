FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip && \
    rm -rf /var/lib/apt/lists/*

# httpx-toolkit
RUN wget -qO /tmp/httpx.zip \
    "https://github.com/projectdiscovery/httpx/releases/latest/download/httpx_$(uname -s)_$(uname -m).zip" && \
    unzip /tmp/httpx.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/httpx && \
    rm -f /tmp/httpx.zip

# nuclei
RUN wget -qO /tmp/nuclei.zip \
    "https://github.com/projectdiscovery/nuclei/releases/latest/download/nuclei_$(uname -s)_$(uname -m).zip" && \
    unzip /tmp/nuclei.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/nuclei && \
    rm -f /tmp/nuclei.zip

# nuclei templates
RUN nuclei -update-templates -ud /opt/nuclei-templates

# SecLists wordlists
RUN mkdir -p /opt/wordlists && \
    wget -qO /opt/wordlists/common.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" && \
    wget -qO /opt/wordlists/small.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-small.txt" && \
    wget -qO /opt/wordlists/large.txt \
      "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt"

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
