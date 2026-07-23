FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render's web services expect the app to listen on port 10000 by default.
ENV API_HOST=0.0.0.0 \
    API_PORT=10000 \
    PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["python", "server.py"]
