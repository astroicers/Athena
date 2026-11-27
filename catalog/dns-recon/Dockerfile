FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends dnsutils && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 9102
CMD ["python", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9102"]
