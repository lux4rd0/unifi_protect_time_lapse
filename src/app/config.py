# app/config.py

import os
import json
import logging
import math
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
# UNIFI PROTECT RATE LIMITING
# =============================================================================

# UniFi Protect's actual rate limit (requests per second)
UNIFI_PROTECT_RATE_LIMIT = int(os.getenv("UNIFI_PROTECT_RATE_LIMIT", "10"))

# Safety buffer - use only this percentage of the rate limit
RATE_LIMIT_SAFETY_BUFFER = float(os.getenv("RATE_LIMIT_SAFETY_BUFFER", "0.8"))  # 80%

# Effective rate limit we'll design around
EFFECTIVE_RATE_LIMIT = int(
    UNIFI_PROTECT_RATE_LIMIT * RATE_LIMIT_SAFETY_BUFFER
)  # 8 req/sec

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

# Auto-calculate concurrent limit based on rate limits ("auto") or set manual limit (number)
FETCH_CONCURRENT_LIMIT_MODE = os.getenv("FETCH_CONCURRENT_LIMIT_MODE", "auto").lower()
FETCH_CONCURRENT_LIMIT_MANUAL = int(os.getenv("FETCH_CONCURRENT_LIMIT_MANUAL", "5"))

# =============================================================================
# CAMERA DISTRIBUTION SETTINGS (Rate-Limit Aware)
# =============================================================================

# Enable camera distribution to avoid rate limits
# "auto" = smart detection based on rate limits and camera count
# "true" = always enable distribution
# "false" = always disable distribution
FETCH_ENABLE_CAMERA_DISTRIBUTION = os.getenv(
    "FETCH_ENABLE_CAMERA_DISTRIBUTION", "auto"
).lower()

# Distribution strategy
# "adaptive" = calculate optimal spacing based on camera count and rate limits
# "fixed" = always use FETCH_CAMERA_OFFSET_SECONDS
FETCH_DISTRIBUTION_STRATEGY = os.getenv(
    "FETCH_DISTRIBUTION_STRATEGY", "adaptive"
).lower()

# Thresholds for auto mode decision making
FETCH_DISTRIBUTION_MIN_CAMERAS = int(os.getenv("FETCH_DISTRIBUTION_MIN_CAMERAS", "4"))

# Distribution calculation parameters
FETCH_DISTRIBUTION_WINDOW_SECONDS = int(
    os.getenv("FETCH_DISTRIBUTION_WINDOW_SECONDS", "60")
)
FETCH_MIN_OFFSET_SECONDS = int(os.getenv("FETCH_MIN_OFFSET_SECONDS", "1"))
FETCH_MAX_OFFSET_SECONDS = int(os.getenv("FETCH_MAX_OFFSET_SECONDS", "15"))

# Fixed offset (used when strategy = "fixed")
FETCH_CAMERA_OFFSET_SECONDS = int(os.getenv("FETCH_CAMERA_OFFSET_SECONDS", "5"))

# Monitoring and diagnostics
FETCH_LOG_SLOT_UTILIZATION = os.getenv(
    "FETCH_LOG_SLOT_UTILIZATION", "True"
).lower() in [
    "true",
    "1",
    "t",
    "y",
    "yes",
]

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
# RATE-LIMIT AWARE FUNCTIONS
# =============================================================================


def calculate_max_simultaneous_intervals() -> int:
    """Calculate the maximum number of intervals that can execute simultaneously."""
    if len(FETCH_INTERVALS) <= 1:
        return 1

    # Check alignment over one full cycle (LCM of all intervals)
    def gcd(a, b):
        while b:
            a, b = b, a % b
        return a

    def lcm(a, b):
        return abs(a * b) // gcd(a, b)

    def lcm_multiple(numbers):
        result = numbers[0]
        for i in range(1, len(numbers)):
            result = lcm(result, numbers[i])
        return result

    cycle_length = min(3600, lcm_multiple(FETCH_INTERVALS))  # Cap at 1 hour

    max_simultaneous = 1
    for timestamp in range(0, cycle_length, 60):  # Check every minute
        simultaneous = len([i for i in FETCH_INTERVALS if timestamp % i == 0])
        max_simultaneous = max(max_simultaneous, simultaneous)

    return max_simultaneous


def calculate_effective_concurrent_limit() -> int:
    """Calculate effective concurrent limit based on rate limits."""
    if FETCH_CONCURRENT_LIMIT_MODE == "manual":
        return FETCH_CONCURRENT_LIMIT_MANUAL

    # Auto-calculate based on rate limits
    max_simultaneous_intervals = calculate_max_simultaneous_intervals()
    effective_limit = EFFECTIVE_RATE_LIMIT // max_simultaneous_intervals

    # Ensure at least 1 camera can capture
    return max(1, effective_limit)


def should_use_camera_distribution(camera_count: int) -> bool:
    """
    Determine if camera distribution should be used based on rate limits and camera count.
    """
    if FETCH_ENABLE_CAMERA_DISTRIBUTION == "true":
        return True
    elif FETCH_ENABLE_CAMERA_DISTRIBUTION == "false":
        return False
    else:  # "auto"
        effective_concurrent_limit = calculate_effective_concurrent_limit()

        # Small deployments - no distribution needed if under rate limits
        if camera_count <= FETCH_DISTRIBUTION_MIN_CAMERAS:
            return False

        # Check if we would exceed rate limits without distribution
        max_simultaneous_intervals = calculate_max_simultaneous_intervals()
        peak_requests_without_distribution = camera_count * max_simultaneous_intervals

        if peak_requests_without_distribution > UNIFI_PROTECT_RATE_LIMIT:
            return True

        # Check if we exceed effective concurrent limit
        return camera_count > effective_concurrent_limit


def calculate_optimal_offset_seconds(camera_count: int) -> int:
    """
    Calculate optimal offset timing based on camera count and rate limits.
    """
    if FETCH_DISTRIBUTION_STRATEGY == "fixed":
        return FETCH_CAMERA_OFFSET_SECONDS

    # Calculate max cameras per slot considering interval alignment
    max_simultaneous_intervals = calculate_max_simultaneous_intervals()
    max_cameras_per_slot = EFFECTIVE_RATE_LIMIT // max_simultaneous_intervals

    if camera_count <= max_cameras_per_slot:
        return 0  # No distribution needed

    # Calculate how many time slots we need
    slots_needed = math.ceil(camera_count / max_cameras_per_slot)

    # Calculate spacing to fit within the configured window
    calculated_offset = FETCH_DISTRIBUTION_WINDOW_SECONDS // slots_needed

    # Apply configured min/max bounds
    optimal_offset = max(
        FETCH_MIN_OFFSET_SECONDS, min(calculated_offset, FETCH_MAX_OFFSET_SECONDS)
    )

    return optimal_offset


def validate_rate_limit_compliance(camera_count: int) -> bool:
    """
    Validate that current configuration won't exceed rate limits.
    """
    max_simultaneous_intervals = calculate_max_simultaneous_intervals()

    if not should_use_camera_distribution(camera_count):
        # No distribution - all cameras capture simultaneously
        peak_requests = camera_count * max_simultaneous_intervals

        if peak_requests > UNIFI_PROTECT_RATE_LIMIT:
            logging.warning(
                f"⚠️  Rate limit risk: {peak_requests} req/sec > {UNIFI_PROTECT_RATE_LIMIT} req/sec"
            )
            logging.warning(
                "   Consider enabling camera distribution or reducing camera count"
            )
            return False
    else:
        # With distribution - check if our slots respect rate limits
        optimal_offset = calculate_optimal_offset_seconds(camera_count)
        max_cameras_per_slot = EFFECTIVE_RATE_LIMIT // max_simultaneous_intervals

        slots_needed = math.ceil(camera_count / max_cameras_per_slot)
        actual_cameras_per_slot = math.ceil(camera_count / slots_needed)
        peak_requests = actual_cameras_per_slot * max_simultaneous_intervals

        if peak_requests > UNIFI_PROTECT_RATE_LIMIT:
            logging.warning(
                f"⚠️  Rate limit risk with distribution: {peak_requests} req/sec > {UNIFI_PROTECT_RATE_LIMIT} req/sec"
            )
            logging.warning("   Consider increasing FETCH_DISTRIBUTION_WINDOW_SECONDS")
            return False

    logging.info("✅ Rate limit compliance: Configuration should stay within limits")
    return True


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

    if FETCH_ENABLE_CAMERA_DISTRIBUTION not in ["auto", "true", "false"]:
        errors.append(
            "FETCH_ENABLE_CAMERA_DISTRIBUTION must be 'auto', 'true', or 'false'"
        )

    if FETCH_DISTRIBUTION_STRATEGY not in ["adaptive", "fixed"]:
        errors.append("FETCH_DISTRIBUTION_STRATEGY must be 'adaptive' or 'fixed'")

    if UNIFI_PROTECT_RATE_LIMIT <= 0:
        errors.append("UNIFI_PROTECT_RATE_LIMIT must be positive")

    if not 0 < RATE_LIMIT_SAFETY_BUFFER <= 1:
        errors.append("RATE_LIMIT_SAFETY_BUFFER must be between 0 and 1")

    try:
        from datetime import datetime

        datetime.strptime(TIMELAPSE_CREATION_TIME, "%H:%M")
    except ValueError:
        errors.append("TIMELAPSE_CREATION_TIME must be in HH:MM format")

    return errors


def find_common_aligned_timestamp() -> int:
    """
    Find the optimal start timestamp for all intervals.

    If FETCH_TOP_OF_THE_MINUTE is True: ALL intervals start at next minute boundary.
    If False: Use LCM for perfect alignment (may wait longer).

    Returns:
        Unix timestamp where intervals should start
    """
    from datetime import datetime
    import math

    now = datetime.now()
    current_timestamp = int(now.timestamp())

    if FETCH_TOP_OF_THE_MINUTE:
        # ALL intervals start at the same time - next minute boundary
        next_minute = ((current_timestamp // 60) + 1) * 60

        wait_seconds = next_minute - current_timestamp
        logging.info(f"Common start timestamp: {next_minute} (wait {wait_seconds}s)")

        return next_minute
    else:
        # Use LCM for perfect alignment (may wait longer)
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        def lcm(a, b):
            return abs(a * b) // gcd(a, b)

        def lcm_multiple(numbers):
            result = numbers[0]
            for i in range(1, len(numbers)):
                result = lcm(result, numbers[i])
            return result

        alignment_period = lcm_multiple(FETCH_INTERVALS)
        next_aligned = ((current_timestamp // alignment_period) + 1) * alignment_period

        wait_seconds = next_aligned - current_timestamp
        logging.info(f"LCM alignment: {next_aligned} (wait {wait_seconds}s)")

        return next_aligned


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
