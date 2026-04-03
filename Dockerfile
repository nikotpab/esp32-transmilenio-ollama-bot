FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY proxy_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY proxy_server/bot.py .
COPY proxy_server/transmilenio_data.py .
COPY .env .

# Set environment variable to make Python print directly to stdout/stderr
ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
