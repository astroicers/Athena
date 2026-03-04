FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Optional: install subfinder for enhanced subdomain enumeration
# RUN apt-get update && apt-get install -y wget && \
#     wget -qO /tmp/subfinder.tar.gz https://github.com/projectdiscovery/subfinder/releases/latest/download/subfinder_linux_amd64.tar.gz && \
#     tar -xzf /tmp/subfinder.tar.gz -C /usr/local/bin subfinder && \
#     rm /tmp/subfinder.tar.gz

CMD ["python", "-m", "server"]
