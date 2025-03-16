# Use official Alpine as base
FROM alpine:3.21.3

# Add build arguments for version and build time
ARG VERSION="0.0.0"
ARG BUILD_DATE="1970-01-01T00:00:00Z"

# Set environment variables for version info
ENV UNIFI_PROTECT_TIME_LAPSE_VERSION=$VERSION \
    UNIFI_PROTECT_TIME_LAPSE_BUILD_DATE=$BUILD_DATE

# Install Python and system dependencies
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    py3-setuptools \
    py3-wheel \
    ffmpeg \
    tzdata \
    gcc \
    musl-dev

# Create a virtual environment
RUN python3 -m venv /venv

# Activate virtual environment and install dependencies
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Set working directory
WORKDIR /app/unifi_protect_time_lapse

# Copy application code
COPY src/app/ ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/unifi_protect_time_lapse \
    PATH="/venv/bin:$PATH"

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ps aux | grep main.py | grep -v grep || exit 1

# Run the main script
CMD ["python3", "./main.py"]
