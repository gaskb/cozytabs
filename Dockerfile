FROM python:3.12-slim

# Install system dependencies: ffmpeg for yt-dlp audio/video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_DIR=/tmp/cozytabs

CMD ["python", "bot.py"]
