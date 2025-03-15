# Use an official Python runtime as a parent image with a specific Alpine version
FROM python:3.13.2-alpine3.21 AS builder

# Create a virtual environment for dependency isolation
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install build dependencies for any potential compilations
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    python3-dev

# Install Python dependencies into the virtual environment
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Start a clean image for the final build
FROM python:3.13.2-alpine3.21

# Install only runtime dependencies
RUN apk add --no-cache ffmpeg tzdata

# Copy the virtual environment from the builder stage
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

# Set the working directory
WORKDIR /app/unifi_time_lapse

# Copy application code
COPY src/app/ ./

# Set non-root user for better security
RUN adduser -D appuser
USER appuser

# Add healthcheck to monitor application health
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ps aux | grep main.py | grep -v grep || exit 1

# Run the main script when the container launches
CMD ["python3", "./main.py"]