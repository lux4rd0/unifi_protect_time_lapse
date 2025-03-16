# app/config.py

import os
import json
from typing import Dict, List, Optional

# =============================================================================
# UNIFI PROTECT SETTINGS
# =============================================================================
UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST", "unifi01.tylephony.com"
)
UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT", "7441"
)

# =============================================================================
# CAMERA CONFIGURATION
# =============================================================================

# Default camera configuration with name, stream ID, and intervals
UNIFI_PROTECT_TIME_LAPSE_DEFAULT_CAMERAS = [
    {"name": "cam-back", "stream_id": "abc123", "intervals": [15, 60]},
    {
        "name": "cam-front",
        "stream_id": "def456",
        "intervals": [60],
    },
]

# Parse camera configuration from environment variable
UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG_JSON = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG", ""
)
if UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG_JSON:
    try:
        UNIFI_PROTECT_TIME_LAPSE_CAMERAS = json.loads(
            UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG_JSON
        )
    except Exception as e:
        print(
            f"Error parsing UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG: {e}. Using defaults."
        )
        UNIFI_PROTECT_TIME_LAPSE_CAMERAS = UNIFI_PROTECT_TIME_LAPSE_DEFAULT_CAMERAS
else:
    UNIFI_PROTECT_TIME_LAPSE_CAMERAS = UNIFI_PROTECT_TIME_LAPSE_DEFAULT_CAMERAS

# Get a list of all camera names
UNIFI_PROTECT_TIME_LAPSE_CAMERA_NAMES = [
    camera["name"] for camera in UNIFI_PROTECT_TIME_LAPSE_CAMERAS
]

# Get a list of all unique intervals
UNIFI_PROTECT_TIME_LAPSE_FETCH_INTERVALS = sorted(
    list(
        set(
            interval
            for camera in UNIFI_PROTECT_TIME_LAPSE_CAMERAS
            for interval in camera["intervals"]
        )
    )
)

# Create a lookup of which cameras to process for each interval
UNIFI_PROTECT_TIME_LAPSE_CAMERAS_BY_INTERVAL = {
    interval: [
        camera["name"]
        for camera in UNIFI_PROTECT_TIME_LAPSE_CAMERAS
        if interval in camera["intervals"]
    ]
    for interval in UNIFI_PROTECT_TIME_LAPSE_FETCH_INTERVALS
}


# Function to build RTSPS URL for a camera
def UNIFI_PROTECT_TIME_LAPSE_get_camera_rtsps_url(camera_name: str) -> Optional[str]:
    for camera in UNIFI_PROTECT_TIME_LAPSE_CAMERAS:
        if camera["name"] == camera_name:
            return f"rtsps://{UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST}:{UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT}/{camera['stream_id']}?enableSrtp"
    return None


# =============================================================================
# FEATURE TOGGLES
# =============================================================================

# Whether to fetch images from cameras
UNIFI_PROTECT_TIME_LAPSE_FETCH_IMAGE_ENABLED = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_FETCH_IMAGE_ENABLED", "True"
).lower() in ["true", "1", "t", "y", "yes"]

# Whether to create timelapse videos
UNIFI_PROTECT_TIME_LAPSE_CREATE_TIMELAPSE_ENABLED = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CREATE_TIMELAPSE_ENABLED", "True"
).lower() in ["true", "1", "t", "y", "yes"]

# =============================================================================
# PATH CONFIGURATIONS
# =============================================================================

# Base directory for storing fetched images
UNIFI_PROTECT_TIME_LAPSE_IMAGE_OUTPUT_PATH = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_IMAGE_OUTPUT_PATH", "output/images"
)

# Base directory for storing timelapse videos
UNIFI_PROTECT_TIME_LAPSE_VIDEO_OUTPUT_PATH = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_VIDEO_OUTPUT_PATH", "output/videos"
)

# =============================================================================
# FETCH TIMING SETTINGS
# =============================================================================

# Timeout for each interval - specified as a percentage of the interval
UNIFI_PROTECT_TIME_LAPSE_TIMEOUT_PERCENTAGE = float(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_TIMEOUT_PERCENTAGE", "0.8")
)

# Calculate timeout for each interval (as a dictionary)
UNIFI_PROTECT_TIME_LAPSE_INTERVAL_TIMEOUTS = {
    interval: max(
        min(int(interval * UNIFI_PROTECT_TIME_LAPSE_TIMEOUT_PERCENTAGE), interval - 1),
        5,
    )
    for interval in UNIFI_PROTECT_TIME_LAPSE_FETCH_INTERVALS
}

# Align with top of minute for consistent timestamping
UNIFI_PROTECT_TIME_LAPSE_FETCH_TOP_OF_THE_MINUTE = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_FETCH_TOP_OF_THE_MINUTE", "True"
).lower() in ["true", "1", "t", "y", "yes"]

# Optimization for multiple intervals - copy images between intervals when possible
UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING", "True"
).lower() in ["true", "1", "t", "y", "yes"]

# =============================================================================
# FETCH RETRY SETTINGS
# =============================================================================

# Maximum retries for failed image fetches
UNIFI_PROTECT_TIME_LAPSE_FETCH_MAX_RETRIES = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_FETCH_MAX_RETRIES", "3")
)

# Delay between retry attempts in seconds
UNIFI_PROTECT_TIME_LAPSE_FETCH_RETRY_DELAY = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_FETCH_RETRY_DELAY", "2")
)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging level (INFO, ERROR, DEBUG, etc.)
UNIFI_PROTECT_TIME_LAPSE_LOGGING_LEVEL = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_LOGGING_LEVEL", "INFO"
).upper()

# Whether to log detailed summaries at INFO level
UNIFI_PROTECT_TIME_LAPSE_HOURLY_SUMMARY_ENABLED = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_HOURLY_SUMMARY_ENABLED", "True"
).lower() in ["true", "1", "t", "y", "yes"]

# Interval between summary logs in seconds (default: 3600 = 1 hour)
# Can be set to smaller values like 60 for more frequent summaries
UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS", "3600")
)

# =============================================================================
# FFMPEG CONFIGURATIONS
# =============================================================================

# Frame rate for timelapse videos
UNIFI_PROTECT_TIME_LAPSE_FFMPEG_FRAME_RATE = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_FFMPEG_FRAME_RATE", "30")
)

# Video encoding quality factor
UNIFI_PROTECT_TIME_LAPSE_FFMPEG_CONSTANT_RATE_FACTOR = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_FFMPEG_CONSTANT_RATE_FACTOR", "25")
)

# Whether to overwrite existing files
UNIFI_PROTECT_TIME_LAPSE_FFMPEG_OVERWRITE_FILE = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_FFMPEG_OVERWRITE_FILE", "False"
).lower() in ["true", "1", "t", "y", "yes"]

# Whether to delete images after successful video creation
UNIFI_PROTECT_TIME_LAPSE_FFMPEG_DELETE_IMAGES_AFTER_SUCCESS = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_FFMPEG_DELETE_IMAGES_AFTER_SUCCESS", "False"
).lower() in ["true", "1", "t", "y", "yes"]

# Number of concurrent video creation tasks
UNIFI_PROTECT_TIME_LAPSE_FFMPEG_CONCURRENT_CREATION = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_FFMPEG_CONCURRENT_CREATION", "1")
)

# =============================================================================
# FFMPEG CAPTURE TECHNIQUES
# =============================================================================

# Frame capture technique (options: "standard", "iframe", "blend")
UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE", "standard"
).lower()

# Number of frames to blend (when using "blend" technique)
UNIFI_PROTECT_TIME_LAPSE_BLEND_FRAMES = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_BLEND_FRAMES", "2")
)

# Maximum wait time for I-frame in seconds (when using "iframe" technique)
UNIFI_PROTECT_TIME_LAPSE_IFRAME_TIMEOUT = float(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_IFRAME_TIMEOUT", "2.0")
)

# Capture technique configurations
UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUES = {
    "standard": {
        "description": "Standard single frame capture",
        "ffmpeg_extra_args": [],
    },
    "iframe": {
        "description": "Selects only I-frames for higher quality",
        "ffmpeg_extra_args": ["-vf", "select='eq(pict_type,I)'", "-vsync", "vfr"],
    },
    "blend": {
        "description": "Blends multiple frames to reduce motion blur",
        "ffmpeg_extra_args": [
            "-filter_complex",
            "[0:v]tblend=all_mode=average[out]",
            "-map",
            "[out]",
        ],
    },
}

# Get the active capture technique configuration
UNIFI_PROTECT_TIME_LAPSE_ACTIVE_TECHNIQUE = (
    UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUES.get(
        UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE,
        UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUES["standard"],
    )
)

# =============================================================================
# FFMPEG VIDEO QUALITY PRESETS
# =============================================================================

# Video quality preset (options: "medium", "high", "custom")
UNIFI_PROTECT_TIME_LAPSE_VIDEO_QUALITY_PRESET = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_VIDEO_QUALITY_PRESET", "medium"
).lower()

# Custom quality settings (used when preset is "custom")
UNIFI_PROTECT_TIME_LAPSE_CUSTOM_CRF = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_CUSTOM_CRF", "23")
)
UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PRESET = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PRESET", "medium"
)
UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PIX_FMT = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PIX_FMT", "yuv420p"
)
UNIFI_PROTECT_TIME_LAPSE_CUSTOM_COLOR_SETTINGS = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CUSTOM_COLOR_SETTINGS", "False"
).lower() in ["true", "1", "t", "y", "yes"]

# Preset configurations
UNIFI_PROTECT_TIME_LAPSE_VIDEO_PRESETS = {
    "medium": {
        "crf": 25,  # Constant Rate Factor (lower = higher quality)
        "preset": "medium",  # Encoding speed preset
        "pix_fmt": "yuv420p",  # Pixel format with 4:2:0 subsampling
        "color_settings": False,  # Whether to use explicit color space settings
    },
    "high": {
        "crf": 18,  # Lower CRF for higher quality
        "preset": "slow",  # Slower preset for better compression
        "pix_fmt": "yuv444p",  # Full color information without subsampling
        "color_settings": True,  # Use explicit color space settings
    },
    "custom": {
        "crf": UNIFI_PROTECT_TIME_LAPSE_CUSTOM_CRF,
        "preset": UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PRESET,
        "pix_fmt": UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PIX_FMT,
        "color_settings": UNIFI_PROTECT_TIME_LAPSE_CUSTOM_COLOR_SETTINGS,
    },
}

# Get the active preset configuration (default to medium if specified preset not found)
UNIFI_PROTECT_TIME_LAPSE_ACTIVE_PRESET = UNIFI_PROTECT_TIME_LAPSE_VIDEO_PRESETS.get(
    UNIFI_PROTECT_TIME_LAPSE_VIDEO_QUALITY_PRESET,
    UNIFI_PROTECT_TIME_LAPSE_VIDEO_PRESETS["medium"],
)

# =============================================================================
# TIMELAPSE CREATION SCHEDULING
# =============================================================================

# Time of day to start creating timelapses
UNIFI_PROTECT_TIME_LAPSE_CREATION_TIME = os.getenv(
    "UNIFI_PROTECT_TIME_LAPSE_CREATION_TIME", "01:00"
)

# Number of days ago to include in timelapses
UNIFI_PROTECT_TIME_LAPSE_DAYS_AGO = int(
    os.getenv("UNIFI_PROTECT_TIME_LAPSE_DAYS_AGO", "1")
)
