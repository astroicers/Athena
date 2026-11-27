FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
EXPOSE 9103
CMD ["python", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9103"]
