# UniFi Protect Time-lapse (API-based)

A modern, API-based solution for creating time-lapse videos from UniFi Protect cameras. This application uses the UniFi Protect REST API to capture camera snapshots at configurable intervals and compiles them into high-quality time-lapse videos.

## Overview

UniFi Protect Time-lapse connects to your UniFi Protect system via its REST API to capture camera snapshots at configurable intervals. These snapshots are then automatically compiled into time-lapse videos daily, giving you a condensed view of what happened throughout the day.

### Key Improvements in This Version

- **API-based**: Uses UniFi Protect's REST API instead of RTSP streams for much better reliability
- **Simplified Configuration**: No more complex stream IDs - just use camera names
- **Automatic Camera Discovery**: Discovers all cameras automatically from your UniFi Protect system
- **Smart Quality Detection**: Automatically detects which cameras support high-quality snapshots
- **Better Error Handling**: Comprehensive retry logic and graceful handling of disconnected cameras
- **Flexible Camera Selection**: Whitelist, blacklist, or capture all cameras
- **Modern Architecture**: Built with async/await for high performance
- **Image Reuse Optimization**: Intelligently reuses images between intervals to reduce camera load

### Features

- **Multiple Capture Intervals**: Configure different capture frequencies (e.g., every 60 seconds, every 3 minutes)
- **Automatic Camera Discovery**: No need for manual stream ID configuration
- **Smart Quality Selection**: Uses high-quality snapshots when cameras support it
- **Image Reuse Optimization**: Automatically reuses images from shorter intervals when aligned
- **Detailed Status Summaries**: Get regular summaries showing success rates and performance for each camera
- **Configurable Video Quality**: Choose between different video quality presets or create custom settings
- **Flexible Camera Selection**: Choose which cameras to include via whitelist, blacklist, or capture all
- **Flexible Scheduling**: Set when time-lapses are created
- **Docker-Based**: Easy deployment using Docker

## Getting Started

### Prerequisites

- Docker and Docker Compose
- UniFi Protect system with API access
- API key from your UniFi Protect system

### Getting Your API Key

1. Log in to your UniFi Protect web interface
2. Go to **Control Plane** → **Integrations** → **Your API Keys**
3. Click **Generate API Key**
4. Give it a descriptive name (e.g., "Time-lapse Service")
5. Copy the generated API key - you'll need this for configuration

### Deployment

1. Create a `docker-compose.yml` file:

```yaml
name: unifi_protect_time_lapse

services:
  unifi_protect_time_lapse:
    container_name: unifi_protect_time_lapse
    image: lux4rd0/unifi_protect_time_lapse:latest
    restart: always
    volumes:
      - ./output:/app/unifi_protect_time_lapse/output:rw
    environment:
      TZ: America/Chicago

      # =============================================================================
      # UNIFI PROTECT API SETTINGS
      # =============================================================================
      UNIFI_PROTECT_API_KEY: "your_api_key_here"  # 🔑 REQUIRED: Get from Control Plane → Integrations → Your API Keys
      UNIFI_PROTECT_BASE_URL: "https://your-protect-host/proxy/protect/integration/v1"
      UNIFI_PROTECT_VERIFY_SSL: "false"
      UNIFI_PROTECT_REQUEST_TIMEOUT: "30"
      CAMERA_REFRESH_INTERVAL: "300"  # Check for reconnected cameras every 5 minutes
      SNAPSHOT_HIGH_QUALITY: "true"   # Request high resolution snapshots when supported

      # =============================================================================
      # CAMERA CONFIGURATION
      # =============================================================================
      CAMERA_SELECTION_MODE: "all"  # Options: "all", "whitelist", "blacklist"
      # CAMERA_WHITELIST: '["Front Door Cam", "Garage Cam", "Backyard Cam"]'
      # CAMERA_BLACKLIST: '["Private Camera"]'
      
      # Fetch intervals in seconds
      FETCH_INTERVALS: '[60, 180]'

      # =============================================================================
      # FETCH SETTINGS
      # =============================================================================
      FETCH_ENABLED: "true"
      FETCH_TOP_OF_THE_MINUTE: "true"
      FETCH_MAX_RETRIES: "3"
      FETCH_RETRY_DELAY: "2"
      FETCH_CONCURRENT_LIMIT: "5"
      FETCH_IMAGE_REUSE_DELAY: "2.0"  # Delay before attempting image reuse (seconds)

      # =============================================================================
      # TIME-LAPSE SETTINGS
      # =============================================================================
      TIMELAPSE_CREATION_ENABLED: "true"
      TIMELAPSE_CREATION_TIME: "01:00"  # Time to create videos (HH:MM format)
      TIMELAPSE_DAYS_AGO: "1"           # Number of days ago to process

      # =============================================================================
      # VIDEO QUALITY SETTINGS
      # =============================================================================
      FFMPEG_FRAME_RATE: "30"
      FFMPEG_CRF: "23"                    # Video quality (lower = higher quality)
      FFMPEG_PRESET: "medium"             # Encoding speed preset
      FFMPEG_PIXEL_FORMAT: "yuv420p"     # Pixel format
      FFMPEG_OVERWRITE_FILE: "false"
      FFMPEG_DELETE_IMAGES_AFTER_SUCCESS: "false"
      FFMPEG_CONCURRENT_CREATION: "2"

      # =============================================================================
      # LOGGING
      # =============================================================================
      LOGGING_LEVEL: "INFO"
      SUMMARY_ENABLED: "true"
      SUMMARY_INTERVAL_SECONDS: "3600"   # Summary every hour
```

2. Replace `your_api_key_here` with your actual API key
3. Replace `your-protect-host` with your UniFi Protect hostname/IP
4. Run `docker compose up -d`

## Environmental Variables

### Core API Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_API_KEY` | **Required**: API key from UniFi Protect | - | `0hOcBk-nofd7...` |
| `UNIFI_PROTECT_BASE_URL` | **Required**: Base URL to UniFi Protect API | - | `https://unifi.local/proxy/protect/integration/v1` |
| `UNIFI_PROTECT_VERIFY_SSL` | Whether to verify SSL certificates | `false` | `true` |
| `UNIFI_PROTECT_REQUEST_TIMEOUT` | Request timeout in seconds | `30` | `60` |
| `CAMERA_REFRESH_INTERVAL` | How often to check for new/reconnected cameras (seconds) | `300` | `60` |
| `SNAPSHOT_HIGH_QUALITY` | Request high resolution snapshots when supported | `true` | `false` |

### Camera Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CAMERA_SELECTION_MODE` | Camera selection method | `all` | `whitelist`, `blacklist` |
| `CAMERA_WHITELIST` | JSON array of camera names to include (whitelist mode) | `[]` | `'["Front Door", "Garage"]'` |
| `CAMERA_BLACKLIST` | JSON array of camera names to exclude (blacklist mode) | `[]` | `'["Private Cam"]'` |
| `FETCH_INTERVALS` | JSON array of capture intervals in seconds | `[10, 60]` | `[30, 300, 900]` |

### Fetch Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FETCH_ENABLED` | Enable/disable image fetching | `true` | `false` |
| `FETCH_TOP_OF_THE_MINUTE` | Align captures to minute boundaries | `true` | `false` |
| `FETCH_MAX_RETRIES` | Maximum retry attempts for failed captures | `3` | `5` |
| `FETCH_RETRY_DELAY` | Delay between retries in seconds | `2` | `5` |
| `FETCH_CONCURRENT_LIMIT` | Maximum concurrent API requests | `5` | `10` |
| `FETCH_IMAGE_REUSE_DELAY` | Delay before attempting image reuse (seconds) | `2.0` | `1.0` |

### Time-lapse Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TIMELAPSE_CREATION_ENABLED` | Enable/disable video creation | `true` | `false` |
| `TIMELAPSE_CREATION_TIME` | Daily time to create videos (HH:MM) | `01:00` | `03:30` |
| `TIMELAPSE_DAYS_AGO` | Number of days ago to process | `1` | `0` |

### Video Quality Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FFMPEG_FRAME_RATE` | Output video frame rate | `30` | `24` |
| `FFMPEG_CRF` | Video quality (lower = higher quality, 0-51) | `23` | `18` |
| `FFMPEG_PRESET` | Encoding speed preset | `medium` | `slow`, `fast` |
| `FFMPEG_PIXEL_FORMAT` | Pixel format | `yuv420p` | `yuv444p` |
| `FFMPEG_OVERWRITE_FILE` | Overwrite existing videos | `false` | `true` |
| `FFMPEG_DELETE_IMAGES_AFTER_SUCCESS` | Delete images after video creation | `false` | `true` |
| `FFMPEG_CONCURRENT_CREATION` | Concurrent video creation jobs | `2` | `4` |

### Path Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `IMAGE_OUTPUT_PATH` | Directory for storing captured images | `output/images` | `storage/photos` |
| `VIDEO_OUTPUT_PATH` | Directory for storing generated videos | `output/videos` | `storage/videos` |

### Logging Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LOGGING_LEVEL` | Logging verbosity level | `INFO` | `DEBUG`, `WARNING` |
| `SUMMARY_ENABLED` | Enable periodic summary logs | `true` | `false` |
| `SUMMARY_INTERVAL_SECONDS` | Seconds between summary logs | `3600` | `1800` |

## Camera Selection Examples

### Capture All Cameras
```yaml
CAMERA_SELECTION_MODE: "all"
```

### Whitelist Specific Cameras
```yaml
CAMERA_SELECTION_MODE: "whitelist"
CAMERA_WHITELIST: '["Front Door Cam", "Garage Cam", "Backyard Cam"]'
```

### Blacklist Specific Cameras
```yaml
CAMERA_SELECTION_MODE: "blacklist"
CAMERA_BLACKLIST: '["Private Bedroom Cam", "Office Camera"]'
```

## Image Reuse Optimization

One of the key performance features is automatic image reuse between intervals. When you configure multiple intervals that are mathematically related (e.g., 60s and 180s), the application automatically reuses images instead of making duplicate API calls.

### How It Works

**Example with 60s and 180s intervals:**

- **14:39:00** - Both 60s and 180s capture fresh images
- **14:40:00** - Only 60s captures fresh images
- **14:41:00** - Only 60s captures fresh images  
- **14:42:00** - 60s captures fresh + 180s **reuses** from 60s
- **14:43:00** - Only 60s captures fresh images
- **14:44:00** - Only 60s captures fresh images
- **14:45:00** - 60s captures fresh + 180s **reuses** from 60s

### Benefits

- **Reduced Camera Load**: 66% fewer API calls for longer intervals
- **Better Performance**: File copying is much faster than camera snapshots
- **Lower Network Usage**: Fewer API requests to your UniFi Protect system
- **Improved Reliability**: Less chance of camera timeouts or network issues

### Configuration Tips

For optimal reuse, configure intervals that divide evenly:
```yaml
# Good: 180 ÷ 60 = 3 (perfect alignment every 3rd capture)
FETCH_INTERVALS: '[60, 180]'

# Good: 900 ÷ 300 = 3, 300 ÷ 60 = 5  
FETCH_INTERVALS: '[60, 300, 900]'

# Less optimal: 90 doesn't divide evenly into 180
FETCH_INTERVALS: '[90, 180]'
```

The application will automatically detect and log optimization opportunities:
```
Interval optimization: 180s will reuse images from 60s when aligned
180s: ✅ Will be able to reuse images from 60s interval
```

## Usage Commands

The application supports several command-line modes for testing and manual operation:

### Test Camera Connectivity
```bash
docker exec your_container python3 main.py test
```

### Create Time-lapse Videos Now
```bash
docker exec your_container python3 main.py create
```

### Run Only Image Capture
```bash
docker exec your_container python3 main.py fetch
```

### Run Only Video Creation
```bash
docker exec your_container python3 main.py timelapse
```

## Docker Volume Structure

Images and videos are stored in the following structure:

```
output/
├── images/
│   └── [camera_name]/
│       └── [interval]s/
│           └── YYYY/MM/DD/
│               └── [camera_name]_[timestamp].jpg
└── videos/
    └── YYYY/MM/
        └── [camera_name]/
            └── [interval]s/
                └── [camera_name]_YYYYMMDD_[interval]s.mp4
```

Example:
```
output/
├── images/
│   ├── Front_Door_Cam/
│   │   ├── 60s/
│   │   │   └── 2025/06/15/
│   │   │       └── Front_Door_Cam_1718456400.jpg
│   │   └── 180s/
│   │       └── 2025/06/15/
│   └── Garage_Cam/
│       └── 60s/
│           └── 2025/06/15/
└── videos/
    └── 2025/06/
        ├── Front_Door_Cam/
        │   ├── 60s/
        │   │   └── Front_Door_Cam_20250615_60s.mp4
        │   └── 180s/
        │       └── Front_Door_Cam_20250615_180s.mp4
        └── Garage_Cam/
            └── 60s/
                └── Garage_Cam_20250615_60s.mp4
```

## Advanced Configuration

### High Quality Video Settings
For maximum quality videos (larger file sizes):
```yaml
FFMPEG_CRF: "18"                    # Higher quality
FFMPEG_PRESET: "slow"               # Better compression
FFMPEG_PIXEL_FORMAT: "yuv444p"     # Full color information
```

### Fast Processing Settings
For faster processing (lower quality):
```yaml
FFMPEG_CRF: "28"                    # Lower quality
FFMPEG_PRESET: "fast"               # Faster encoding
FFMPEG_CONCURRENT_CREATION: "4"    # More parallel jobs
```

### Custom Interval Examples
```yaml
# Multiple intervals for different purposes
FETCH_INTERVALS: '[30, 300, 900]'   # 30s, 5min, 15min

# High frequency for detailed capture
FETCH_INTERVALS: '[10, 60]'         # 10s, 1min

# Low frequency for overview
FETCH_INTERVALS: '[300, 3600]'      # 5min, 1hour

# Optimized for reuse
FETCH_INTERVALS: '[60, 180, 900]'   # Perfect mathematical alignment
```

### Performance Tuning

For systems with fast storage (SSD/NVMe):
```yaml
FETCH_IMAGE_REUSE_DELAY: "1.0"     # Faster reuse detection
FETCH_CONCURRENT_LIMIT: "10"       # More concurrent requests
```

For systems with slower storage (network drives):
```yaml
FETCH_IMAGE_REUSE_DELAY: "3.0"     # More time for file writes
FETCH_CONCURRENT_LIMIT: "3"        # Fewer concurrent requests
```

### Multiple Site Deployment
To monitor multiple UniFi Protect sites, create separate services:

```yaml
name: unifi_protect_time_lapse_multi

services:
  site_main:
    container_name: unifi_protect_time_lapse_main
    image: lux4rd0/unifi_protect_time_lapse:latest
    volumes:
      - ./output_main:/app/unifi_protect_time_lapse/output:rw
    environment:
      UNIFI_PROTECT_API_KEY: "main_site_api_key"
      UNIFI_PROTECT_BASE_URL: "https://main.example.com/proxy/protect/integration/v1"
      # ... other settings
      
  site_remote:
    container_name: unifi_protect_time_lapse_remote
    image: lux4rd0/unifi_protect_time_lapse:latest
    volumes:
      - ./output_remote:/app/unifi_protect_time_lapse/output:rw
    environment:
      UNIFI_PROTECT_API_KEY: "remote_site_api_key"
      UNIFI_PROTECT_BASE_URL: "https://remote.example.com/proxy/protect/integration/v1"
      # ... other settings
```

## Monitoring and Status

### Detailed Status Summaries

The application provides detailed summaries at configurable intervals showing:

- Overall success and failure rates
- Per-camera performance statistics
- Number of connected vs disconnected cameras
- Image quality information (HD vs Standard)
- Image reuse statistics

Example summary:
```
Fetch Summary (last 60.0 minutes):
  60s: 358/360 successful (99.4%), last: 09:59:50
    Front_Door_Cam: 358/360 (99.4%)
    Garage_Cam: 360/360 (100.0%)
  180s: 120/120 successful (100.0%), 80 reused, last: 09:57:00
    Front_Door_Cam: 120/120 (100.0%)
    Garage_Cam: 120/120 (100.0%)
```

### Camera Status Information

At startup and during operation, you'll see detailed camera information:
```
Available cameras: "Front Door Cam", "Garage Cam", "Backyard Cam"
  ✓ Front Door Cam (CONNECTED) - G4-Doorbell [HD]
  ✓ Garage Cam (CONNECTED) - G4-Pro [HD]  
  ✗ Backyard Cam (DISCONNECTED) - G3-Instant [SD]
```

Legend:
- `✓` = Connected camera
- `✗` = Disconnected camera  
- `[HD]` = Supports high-quality snapshots
- `[SD]` = Standard quality only

### Image Reuse Status

When intervals are properly aligned, you'll see optimization messages:
```
Interval optimization: 180s will reuse images from 60s when aligned
180s: ✅ Will be able to reuse images from 60s interval
180s: Attempting to reuse images from 60s interval at timestamp 1750016340
180s: Successfully reused 7 images from 60s interval
180s: Reused 7 images from smaller intervals
```

## Troubleshooting

### API Connection Issues

**No cameras discovered:**
- Verify your API key is correct
- Check that the base URL is accessible
- Ensure your UniFi Protect system supports the integration API

**API key errors:**
- Go to Control Plane → Integrations → Your API Keys in UniFi Protect
- Generate a new API key
- Make sure the API key has the necessary permissions

### Camera Issues

**Cameras not being captured:**
- Check camera selection mode and whitelist/blacklist settings
- Verify camera names match exactly (check logs for "Available cameras")
- Ensure cameras are connected and online in UniFi Protect

**Some cameras fail with "400 Bad Request":**
- This usually means the camera doesn't support high-quality snapshots
- The application will automatically detect this and use standard quality
- Check logs for `[HD]` vs `[SD]` indicators

### Image Reuse Issues

**Images not being reused despite aligned intervals:**
- Check that `FETCH_IMAGE_REUSE_DELAY` allows enough time for file writes
- Verify intervals are mathematically aligned (larger ÷ smaller = whole number)
- Look for alignment verification messages in logs

**Reuse failing with file not found errors:**
- Increase `FETCH_IMAGE_REUSE_DELAY` for slower storage systems
- Check filesystem permissions and available disk space
- Verify both interval directories exist and are writable

### Video Creation Issues

**No videos created:**
- Check that images were captured successfully
- Verify there are enough images for the time period
- Check container logs for FFmpeg errors
- Ensure sufficient disk space

**Video quality issues:**
- Adjust `FFMPEG_CRF` (lower values = higher quality)
- Change `FFMPEG_PRESET` to "slow" for better compression
- Use `yuv444p` pixel format for full color information

### Performance Issues

**High API load:**
- Increase `CAMERA_REFRESH_INTERVAL` to check for cameras less frequently
- Reduce `FETCH_CONCURRENT_LIMIT` to limit simultaneous requests
- Use longer capture intervals
- Ensure intervals are properly aligned for image reuse

**Slow video creation:**
- Increase `FFMPEG_CONCURRENT_CREATION` for more parallel jobs
- Use faster presets like "fast" or "veryfast"
- Consider using a higher CRF value for faster encoding

**Storage performance:**
- For fast storage: Reduce `FETCH_IMAGE_REUSE_DELAY` to 1.0s
- For slow storage: Increase `FETCH_IMAGE_REUSE_DELAY` to 3.0s or higher
- Monitor disk I/O during operation

### Network Issues

**SSL certificate errors:**
```yaml
UNIFI_PROTECT_VERIFY_SSL: "false"
```

**Timeout issues:**
```yaml
UNIFI_PROTECT_REQUEST_TIMEOUT: "60"  # Increase timeout
```

**Connection refused:**
- Verify the UniFi Protect hostname/IP is correct
- Check that the integration API is enabled
- Ensure network connectivity between Docker and UniFi Protect

## Migration from RTSP Version

If you're migrating from the older RTSP-based version:

### Configuration Changes

1. **Replace RTSP settings with API settings:**
   ```yaml
   # Old RTSP settings (remove these)
   # UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST: unifi.local
   # UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT: '7441'
   
   # New API settings (add these)
   UNIFI_PROTECT_API_KEY: "your_api_key_here"
   UNIFI_PROTECT_BASE_URL: "https://unifi.local/proxy/protect/integration/v1"
   ```

2. **Simplify camera configuration:**
   ```yaml
   # Old complex camera config (remove this)
   # UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG: '[{"name":"cam-front","stream_id":"abc123","intervals":[60]}]'
   
   # New simple config (add these)
   CAMERA_SELECTION_MODE: "whitelist"
   CAMERA_WHITELIST: '["Front Door Cam"]'
   FETCH_INTERVALS: '[60]'
   ```

3. **Update environment variable names:**
   - Most variables have been simplified (remove `UNIFI_PROTECT_TIME_LAPSE_` prefix)
   - Check the environmental variables table above for current names

### Benefits of Migration

- **99% more reliable** - no more RTSP connection issues
- **Simpler configuration** - no manual stream ID management
- **Better performance** - direct API calls instead of video stream processing  
- **Automatic discovery** - finds cameras automatically
- **Smart quality** - uses best quality each camera supports
- **Better error handling** - comprehensive retry and recovery logic
- **Image reuse optimization** - significant reduction in API calls and camera load

## Support and Resources

- **Repository**: https://github.com/lux4rd0/unifi_protect_time_lapse
- **Documentation**: https://labs.lux4rd0.com/applications/unifi-protect-time-lapse/
- **Docker Hub**: https://hub.docker.com/r/lux4rd0/unifi_protect_time_lapse

For issues and feature requests, please use the GitHub repository's issue tracker.
