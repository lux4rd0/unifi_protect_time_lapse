# app/config.py

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# =============================================================================
# UNIFI PROTECT API SETTINGS
# =============================================================================

UNIFI_PROTECT_API_KEY = os.getenv("UNIFI_PROTECT_API_KEY", "")

UNIFI_PROTECT_BASE_URL = os.getenv(
    "UNIFI_PROTECT_BASE_URL",
    "https://unifi01.tylephony.com/proxy/protect/integration/v1",
)

# SSL verification setting
UNIFI_PROTECT_VERIFY_SSL = os.getenv("UNIFI_PROTECT_VERIFY_SSL", "False").lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

# Request timeout in seconds
UNIFI_PROTECT_REQUEST_TIMEOUT = int(os.getenv("UNIFI_PROTECT_REQUEST_TIMEOUT", "30"))

# Camera refresh interval in seconds (how often to check for new/reconnected cameras)
CAMERA_REFRESH_INTERVAL = int(os.getenv("CAMERA_REFRESH_INTERVAL", "300"))

# Whether to request high quality snapshots (1080P+)
SNAPSHOT_HIGH_QUALITY = os.getenv("SNAPSHOT_HIGH_QUALITY", "True").lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

# =============================================================================
# CAMERA CONFIGURATION
# =============================================================================

# Camera selection mode: "all", "whitelist", or "blacklist"
CAMERA_SELECTION_MODE = os.getenv("CAMERA_SELECTION_MODE", "all").lower()

# Camera whitelist (only capture these cameras when mode is "whitelist")
CAMERA_WHITELIST_JSON = os.getenv("CAMERA_WHITELIST", "")
if CAMERA_WHITELIST_JSON:
    try:
        CAMERA_WHITELIST = json.loads(CAMERA_WHITELIST_JSON)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing CAMERA_WHITELIST: {e}. Using empty list.")
        CAMERA_WHITELIST = []
else:
    CAMERA_WHITELIST = []

# Camera blacklist (skip these cameras when mode is "blacklist")
CAMERA_BLACKLIST_JSON = os.getenv("CAMERA_BLACKLIST", "")
if CAMERA_BLACKLIST_JSON:
    try:
        CAMERA_BLACKLIST = json.loads(CAMERA_BLACKLIST_JSON)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing CAMERA_BLACKLIST: {e}. Using empty list.")
        CAMERA_BLACKLIST = []
else:
    CAMERA_BLACKLIST = []

# Fetch intervals in seconds
FETCH_INTERVALS_JSON = os.getenv("FETCH_INTERVALS", "[10, 60]")
try:
    FETCH_INTERVALS = json.loads(FETCH_INTERVALS_JSON)
except json.JSONDecodeError as e:
    logging.error(f"Error parsing FETCH_INTERVALS: {e}. Using defaults.")
    FETCH_INTERVALS = [10, 60]

# Sort intervals
FETCH_INTERVALS = sorted(FETCH_INTERVALS)

# =============================================================================
# PATH CONFIGURATIONS
# =============================================================================

# Base directory for storing fetched images
IMAGE_OUTPUT_PATH = Path(os.getenv("IMAGE_OUTPUT_PATH", "output/images"))

# Base directory for storing timelapse videos
VIDEO_OUTPUT_PATH = Path(os.getenv("VIDEO_OUTPUT_PATH", "output/videos"))

# =============================================================================
# FETCH TIMING SETTINGS
# =============================================================================

# Align with top of minute for consistent timestamping
FETCH_TOP_OF_THE_MINUTE = os.getenv("FETCH_TOP_OF_THE_MINUTE", "True").lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

# Maximum retries for failed image fetches
FETCH_MAX_RETRIES = int(os.getenv("FETCH_MAX_RETRIES", "3"))

# Delay between retry attempts in seconds
FETCH_RETRY_DELAY = int(os.getenv("FETCH_RETRY_DELAY", "2"))

# Concurrent fetch limit
FETCH_CONCURRENT_LIMIT = int(os.getenv("FETCH_CONCURRENT_LIMIT", "5"))

# Delay to wait for source images to be written before attempting reuse (in seconds)
FETCH_IMAGE_REUSE_DELAY = float(os.getenv("FETCH_IMAGE_REUSE_DELAY", "5.0"))

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging level (INFO, ERROR, DEBUG, etc.)
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO").upper()

# Whether to log detailed summaries at INFO level
SUMMARY_ENABLED = os.getenv("SUMMARY_ENABLED", "True").lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

# Interval between summary logs in seconds (default: 3600 = 1 hour)
SUMMARY_INTERVAL_SECONDS = int(os.getenv("SUMMARY_INTERVAL_SECONDS", "3600"))

# =============================================================================
# FFMPEG CONFIGURATIONS
# =============================================================================

# Frame rate for timelapse videos
FFMPEG_FRAME_RATE = int(os.getenv("FFMPEG_FRAME_RATE", "30"))

# Video encoding quality factor (lower = higher quality)
FFMPEG_CRF = int(os.getenv("FFMPEG_CRF", "23"))

# FFmpeg preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
FFMPEG_PRESET = os.getenv("FFMPEG_PRESET", "medium")

# Whether to overwrite existing files
FFMPEG_OVERWRITE_FILE = os.getenv("FFMPEG_OVERWRITE_FILE", "False").lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

# Whether to delete images after successful video creation
FFMPEG_DELETE_IMAGES_AFTER_SUCCESS = os.getenv(
    "FFMPEG_DELETE_IMAGES_AFTER_SUCCESS", "False"
).lower() in ["true", "1", "t", "y", "yes"]

# Number of concurrent video creation tasks
FFMPEG_CONCURRENT_CREATION = int(os.getenv("FFMPEG_CONCURRENT_CREATION", "2"))

# Pixel format
FFMPEG_PIXEL_FORMAT = os.getenv("FFMPEG_PIXEL_FORMAT", "yuv420p")

# =============================================================================
# FEATURE TOGGLES
# =============================================================================

# Whether to fetch images from cameras
FETCH_ENABLED = os.getenv("FETCH_ENABLED", "True").lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

# Whether to create timelapse videos
TIMELAPSE_CREATION_ENABLED = os.getenv(
    "TIMELAPSE_CREATION_ENABLED", "True"
).lower() in ["true", "1", "t", "y", "yes"]

# =============================================================================
# TIMELAPSE CREATION SCHEDULING
# =============================================================================

# Time of day to start creating timelapses (HH:MM format)
TIMELAPSE_CREATION_TIME = os.getenv("TIMELAPSE_CREATION_TIME", "01:00")

# Number of days ago to include in timelapses
TIMELAPSE_DAYS_AGO = int(os.getenv("TIMELAPSE_DAYS_AGO", "1"))

# Maximum sleep interval before logging status (in seconds)
MAX_SLEEP_INTERVAL = int(os.getenv("MAX_SLEEP_INTERVAL", "3600"))

# =============================================================================
# VALIDATION AND COMPUTED VALUES
# =============================================================================


def validate_config():
    """Validate configuration and return any errors."""
    errors = []

    if not UNIFI_PROTECT_API_KEY:
        errors.append("UNIFI_PROTECT_API_KEY is required")

    if not UNIFI_PROTECT_BASE_URL:
        errors.append("UNIFI_PROTECT_BASE_URL is required")

    if CAMERA_SELECTION_MODE not in ["all", "whitelist", "blacklist"]:
        errors.append(
            "CAMERA_SELECTION_MODE must be 'all', 'whitelist', or 'blacklist'"
        )

    if not FETCH_INTERVALS:
        errors.append("FETCH_INTERVALS must contain at least one interval")

    if any(interval <= 0 for interval in FETCH_INTERVALS):
        errors.append("All FETCH_INTERVALS must be positive integers")

    if FETCH_IMAGE_REUSE_DELAY < 0:
        errors.append("FETCH_IMAGE_REUSE_DELAY must be a positive number")

    try:
        from datetime import datetime

        datetime.strptime(TIMELAPSE_CREATION_TIME, "%H:%M")
    except ValueError:
        errors.append("TIMELAPSE_CREATION_TIME must be in HH:MM format")

    return errors


# Get request headers for JSON responses
def get_json_headers() -> Dict[str, str]:
    return {
        "X-API-Key": UNIFI_PROTECT_API_KEY,
        "Accept": "application/json",
        "User-Agent": "UniFi-Protect-Time-Lapse/2.0",
    }


# Get request headers for image responses
def get_image_headers() -> Dict[str, str]:
    return {
        "X-API-Key": UNIFI_PROTECT_API_KEY,
        "Accept": "image/jpeg",
        "User-Agent": "UniFi-Protect-Time-Lapse/2.0",
    }


# Get request configuration
def get_request_config() -> Dict[str, Any]:
    return {
        "verify": UNIFI_PROTECT_VERIFY_SSL,
        "timeout": UNIFI_PROTECT_REQUEST_TIMEOUT,
    }


def should_process_camera(camera_name: str) -> bool:
    """Determine if a camera should be processed based on selection mode."""
    if CAMERA_SELECTION_MODE == "whitelist":
        return camera_name in CAMERA_WHITELIST
    elif CAMERA_SELECTION_MODE == "blacklist":
        return camera_name not in CAMERA_BLACKLIST
    else:  # "all"
        return True


# Create output directories
def ensure_directories():
    """Create necessary output directories."""
    IMAGE_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    VIDEO_OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
