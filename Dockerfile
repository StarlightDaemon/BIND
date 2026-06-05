# Stage 1: build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-builder /app/src/static/dist /app/src/static/dist

ENV PYTHONPATH=/app

RUN useradd -r -u 1001 -s /bin/false bind

USER bind

CMD ["python", "src/bind.py", "daemon"]
