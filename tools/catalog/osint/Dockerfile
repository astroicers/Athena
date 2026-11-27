FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        whois \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 9104

CMD ["python", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9104"]
