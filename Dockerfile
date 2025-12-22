FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (build tools might be needed for some python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set PYTHONPATH so imports work correctly
ENV PYTHONPATH=/app

# Default command runs the daemon
CMD ["python", "src/abmg.py", "daemon"]
