FROM python:3.12-slim

# Install system dependencies: ffmpeg for yt-dlp audio/video processing and procps for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root appuser and set ownership
RUN useradd -m -u 1000 appuser && \
    mkdir -p /tmp/cozytabs && \
    chown -R appuser:appuser /app /tmp/cozytabs

ENV PYTHONUNBUFFERED=1
ENV DOWNLOAD_DIR=/tmp/cozytabs

USER appuser

HEALTHCHECK --interval=60s --timeout=5s --start-period=15s --retries=3 \
  CMD pgrep -f "python bot.py" > /dev/null || exit 1

CMD ["python", "bot.py"]
