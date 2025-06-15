# Use official Alpine as base
FROM alpine:3.21.3

# Add build arguments for version and build time
ARG VERSION="2.0.0"
ARG BUILD_DATE="1970-01-01T00:00:00Z"

# Set environment variables for version info
ENV UNIFI_PROTECT_TIME_LAPSE_VERSION=$VERSION \
    UNIFI_PROTECT_TIME_LAPSE_BUILD_DATE=$BUILD_DATE

# Install Python and system dependencies (cached layer)
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    ffmpeg \
    tzdata \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev

# Create a virtual environment (cached layer)
RUN python3 -m venv /venv

# Set working directory
WORKDIR /app/unifi_protect_time_lapse

# Copy requirements first (for dependency caching)
COPY requirements.txt .

# Install dependencies (cached if requirements.txt unchanged)
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code (separate layer, rebuilds when code changes)
COPY src/app/ ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/unifi_protect_time_lapse \
    PATH="/venv/bin:$PATH"

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import asyncio; import sys; sys.path.append('.'); from camera_manager import CameraManager; asyncio.run(CameraManager().get_cameras())" || exit 1

# Run the main script
CMD ["python3", "./main.py"]