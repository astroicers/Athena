FROM athena-mcp-base:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Install CloudFox binary
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then CF_ARCH="amd64"; else CF_ARCH="arm64"; fi && \
    curl -sL "https://github.com/BishopFox/cloudfox/releases/latest/download/cloudfox-linux-${CF_ARCH}.zip" -o /tmp/cf.zip && \
    unzip /tmp/cf.zip -d /tmp/cf-extract && \
    mv /tmp/cf-extract/cloudfox /usr/local/bin/cloudfox && \
    chmod +x /usr/local/bin/cloudfox && \
    rm -rf /tmp/cf.zip /tmp/cf-extract

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["python", "-m", "server"]
