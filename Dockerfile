# Use official Alpine as base
FROM alpine:3.21.3

# Add build arguments for version and build time
ARG VERSION="2.0.0"
ARG BUILD_DATE="1970-01-01T00:00:00Z"

# Set environment variables for version info
ENV UNIFI_PROTECT_TIME_LAPSE_VERSION=$VERSION \
    UNIFI_PROTECT_TIME_LAPSE_BUILD_DATE=$BUILD_DATE

# Install system dependencies in a single cached layer
# This layer will be cached unless Alpine base image changes
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
    openssl-dev && \
    python3 -m venv /venv

# Set working directory
WORKDIR /app/unifi_protect_time_lapse

# Copy requirements first (for dependency caching)
# This layer will be cached unless requirements.txt changes
COPY requirements.txt .

# Install Python dependencies in separate cached layer
# This layer will be cached unless requirements.txt changes
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code (this layer rebuilds when code changes)
# Keep this near the end so code changes don't invalidate earlier layers
COPY src/app/ ./

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/unifi_protect_time_lapse \
    PATH="/venv/bin:$PATH"

# Run the main script
CMD ["python3", "./main.py"]