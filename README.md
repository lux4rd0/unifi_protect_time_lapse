# UniFi Protect Time-lapse (API-based)

A modern, API-based solution for creating time-lapse videos from UniFi Protect cameras. This application uses the UniFi Protect REST API to capture camera snapshots at configurable intervals and compiles them into high-quality time-lapse videos.

## Overview

UniFi Protect Time-lapse connects to your UniFi Protect system via its REST API to capture camera snapshots at configurable intervals. These snapshots are then automatically compiled into time-lapse videos daily, giving you a condensed view of what happened throughout the day.

### Key Improvements in This Version

- **API-based**: Uses UniFi Protect's REST API instead of RTSP streams for much better reliability
- **Rate-Limit Aware**: Automatically respects UniFi Protect's 10 req/sec rate limit with intelligent camera distribution
- **Simplified Configuration**: No more complex stream IDs - just use camera names
- **Automatic Camera Discovery**: Discovers all cameras automatically from your UniFi Protect system
- **Smart Quality Detection**: Automatically detects which cameras support high-quality snapshots
- **Better Error Handling**: Comprehensive retry logic and graceful handling of disconnected cameras
- **Flexible Camera Selection**: Whitelist, blacklist, or capture all cameras
- **Modern Architecture**: Built with async/await for high performance

### Features

- **Rate Limit Compliance**: Automatically calculates optimal timing to stay within UniFi Protect's API limits
- **Intelligent Camera Distribution**: Spreads camera requests across time to avoid overwhelming the system
- **Multiple Capture Intervals**: Configure different capture frequencies (e.g., every 60 seconds, every 3 minutes)
- **Automatic Camera Discovery**: No need for manual stream ID configuration
- **Smart Quality Selection**: Uses high-quality snapshots when cameras support it
- **System Validation**: Validates configuration against rate limits before starting
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
      # RATE LIMITING (UniFi Protect API Limits)
      # =============================================================================
      UNIFI_PROTECT_RATE_LIMIT: "10"        # UniFi Protect's actual rate limit (req/sec)
      RATE_LIMIT_SAFETY_BUFFER: "0.8"       # Use 80% of rate limit for safety

      # =============================================================================
      # CAMERA CONFIGURATION
      # =============================================================================
      CAMERA_SELECTION_MODE: "all"  # Options: "all", "whitelist", "blacklist"
      # CAMERA_WHITELIST: '["Front Door Cam", "Garage Cam", "Backyard Cam"]'
      # CAMERA_BLACKLIST: '["Private Camera"]'
      
      # Fetch intervals in seconds
      FETCH_INTERVALS: '[60, 180]'

      # =============================================================================
      # FETCH SETTINGS (Rate-Limit Aware)
      # =============================================================================
      FETCH_ENABLED: "true"
      FETCH_TOP_OF_THE_MINUTE: "true"
      FETCH_MAX_RETRIES: "3"
      FETCH_RETRY_DELAY: "2"

      # Concurrent limiting - auto-calculates based on rate limits
      FETCH_CONCURRENT_LIMIT_MODE: "auto"        # "auto" = calculate from rate limits, "manual" = use manual setting
      FETCH_CONCURRENT_LIMIT_MANUAL: "5"         # Only used if mode = "manual"

      # =============================================================================
      # CAMERA DISTRIBUTION (Automatic Rate Limit Protection)
      # =============================================================================
      FETCH_ENABLE_CAMERA_DISTRIBUTION: "auto"     # auto (smart), true (always), false (never)
      FETCH_DISTRIBUTION_STRATEGY: "adaptive"      # adaptive (calculate from rate limits), fixed (use offset below)
      
      # Auto mode thresholds
      FETCH_DISTRIBUTION_MIN_CAMERAS: "4"          # No distribution if ≤ this many cameras
      
      # Distribution timing calculation (when strategy="adaptive")
      FETCH_DISTRIBUTION_WINDOW_SECONDS: "60"      # Spread cameras across this time window
      FETCH_MIN_OFFSET_SECONDS: "1"                # Minimum time between camera groups
      FETCH_MAX_OFFSET_SECONDS: "15"               # Maximum time between camera groups
      
      # Fixed offset (when strategy="fixed")
      FETCH_CAMERA_OFFSET_SECONDS: "5"             # Fixed seconds between camera groups
      
      # Monitoring and diagnostics
      FETCH_LOG_SLOT_UTILIZATION: "true"           # Show camera slot assignments in logs

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

### Rate Limiting Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_RATE_LIMIT` | UniFi Protect's API rate limit (requests per second) | `10` | `15` |
| `RATE_LIMIT_SAFETY_BUFFER` | Percentage of rate limit to use (0.0-1.0) | `0.8` | `0.9` |

### Camera Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CAMERA_SELECTION_MODE` | Camera selection method | `all` | `whitelist`, `blacklist` |
| `CAMERA_WHITELIST` | JSON array of camera names to include (whitelist mode) | `[]` | `'["Front Door", "Garage"]'` |
| `CAMERA_BLACKLIST` | JSON array of camera names to exclude (blacklist mode) | `[]` | `'["Private Cam"]'` |
| `FETCH_INTERVALS` | JSON array of capture intervals in seconds | `[10, 60]` | `[30, 300, 900]` |

### Fetch Settings (Rate-Limit Aware)

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FETCH_ENABLED` | Enable/disable image fetching | `true` | `false` |
| `FETCH_TOP_OF_THE_MINUTE` | Align captures to minute boundaries | `true` | `false` |
| `FETCH_MAX_RETRIES` | Maximum retry attempts for failed captures | `3` | `5` |
| `FETCH_RETRY_DELAY` | Delay between retries in seconds | `2` | `5` |
| `FETCH_CONCURRENT_LIMIT_MODE` | Concurrent limit calculation mode | `auto` | `manual` |
| `FETCH_CONCURRENT_LIMIT_MANUAL` | Manual concurrent limit (when mode=manual) | `5` | `10` |

### Camera Distribution (Automatic Rate Limit Protection)

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FETCH_ENABLE_CAMERA_DISTRIBUTION` | Enable camera distribution | `auto` | `true`, `false` |
| `FETCH_DISTRIBUTION_STRATEGY` | Distribution calculation strategy | `adaptive` | `fixed` |
| `FETCH_DISTRIBUTION_MIN_CAMERAS` | Minimum cameras to enable distribution | `4` | `2` |
| `FETCH_DISTRIBUTION_WINDOW_SECONDS` | Time window for distribution | `60` | `120` |
| `FETCH_MIN_OFFSET_SECONDS` | Minimum offset between groups | `1` | `2` |
| `FETCH_MAX_OFFSET_SECONDS` | Maximum offset between groups | `15` | `30` |
| `FETCH_CAMERA_OFFSET_SECONDS` | Fixed offset (when strategy=fixed) | `5` | `10` |
| `FETCH_LOG_SLOT_UTILIZATION` | Log camera slot assignments | `true` | `false` |

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

## Rate Limit Management

This application automatically manages UniFi Protect's API rate limits (10 requests per second) through several mechanisms:

### Automatic Rate Limit Detection

The system automatically:
- Detects how many intervals might execute simultaneously
- Calculates safe concurrent limits based on your camera count
- Warns if your configuration might exceed rate limits
- Suggests optimal settings for your deployment size

### Camera Distribution

For larger deployments (4+ cameras), the system automatically distributes camera requests across time:

```
Example with 12 cameras:
21:30:00 - Cameras 1-4 capture
21:30:05 - Cameras 5-8 capture  
21:30:10 - Cameras 9-12 capture
```

This ensures you never exceed the 10 req/sec limit while maintaining precise timing.

### Rate Limit Configuration Examples

**Small deployment (≤5 cameras):**
```yaml
FETCH_CONCURRENT_LIMIT_MODE: "auto"        # System calculates optimal limits
FETCH_ENABLE_CAMERA_DISTRIBUTION: "auto"   # Enables distribution if needed
```

**Large deployment (20+ cameras):**
```yaml
UNIFI_PROTECT_RATE_LIMIT: "10"            # UniFi's actual limit
RATE_LIMIT_SAFETY_BUFFER: "0.8"           # Use 80% for safety
FETCH_ENABLE_CAMERA_DISTRIBUTION: "true"   # Always enable distribution
FETCH_DISTRIBUTION_STRATEGY: "adaptive"    # Calculate optimal timing
```

**Custom rate limiting:**
```yaml
FETCH_CONCURRENT_LIMIT_MODE: "manual"      # Manual control
FETCH_CONCURRENT_LIMIT_MANUAL: "3"         # Never more than 3 simultaneous requests
```

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

## Usage Commands

The application supports several command-line modes for testing and manual operation:

### Validate System Configuration
```bash
docker exec your_container python3 main.py validate
```
This checks if your configuration will exceed rate limits before starting.

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

## System Status and Monitoring

### Startup Validation

The application validates your configuration at startup:

```
✅ Rate limit compliance: Configuration should stay within limits
✅ System capacity validation passed

Connected cameras: 15
Max simultaneous intervals: 2
Effective concurrent limit: 4
Rate limit analysis: limit=10 req/sec, effective=8 req/sec, max_intervals=2, concurrent_limit=4
```

### Camera Distribution Logging

When camera distribution is enabled, you'll see detailed slot assignments:

```
Camera distribution ENABLED: 15 cameras, strategy: adaptive, offset: 8s
Camera slot assignments (deterministic):
  Slot 0 (+0s): Front Door Cam, Garage Cam, Backyard Cam, Kitchen Cam
  Slot 1 (+8s): Living Room Cam, Bedroom Cam, Office Cam, Basement Cam
  Slot 2 (+16s): Patio Cam, Driveway Cam, Side Yard Cam
```

### Interval-Specific Logging

All operations are clearly tagged by interval:

```
[60s] Captured 15/15 connected cameras (distributed across 3 groups, 8s offset)
[180s] Captured 15/15 connected cameras (distributed across 3 groups, 8s offset)
```

### Rate Limit Headers

The application logs UniFi Protect's rate limit headers so you can monitor usage:

```
RateLimit-Policy: "10-in-1sec"; q=10; w=1
RateLimit: "10-in-1sec"; r=6; t=1    # 6 requests remaining this second
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
```

### Large Deployment Settings
For deployments with 20+ cameras:
```yaml
# Rate limiting
UNIFI_PROTECT_RATE_LIMIT: "10"
RATE_LIMIT_SAFETY_BUFFER: "0.7"           # More conservative buffer

# Camera distribution
FETCH_ENABLE_CAMERA_DISTRIBUTION: "true"   # Always enable
FETCH_DISTRIBUTION_STRATEGY: "adaptive"    # Auto-calculate timing
FETCH_DISTRIBUTION_WINDOW_SECONDS: "120"   # Spread across 2 minutes
FETCH_MAX_OFFSET_SECONDS: "30"            # Allow longer spacing

# Concurrent limits
FETCH_CONCURRENT_LIMIT_MODE: "manual"      # Manual control
FETCH_CONCURRENT_LIMIT_MANUAL: "3"         # Conservative limit
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
- Rate limit compliance status

Example summary:
```
Fetch Summary (last 60.0 minutes):
  60s: 358/360 successful (99.4%), last: 09:59:50
    Front_Door_Cam: 358/360 (99.4%)
    Garage_Cam: 360/360 (100.0%)
  180s: 120/120 successful (100.0%), last: 09:57:00

Rate limit analysis: limit=10 req/sec, effective=8 req/sec, max_intervals=2, concurrent_limit=4
```

### Camera Status Information

At startup and during operation, you'll see detailed camera information:
```
Available cameras: "Front Door Cam", "Garage Cam", "Backyard Cam"
  ✓ Front Door Cam (CONNECTED) - G4-Doorbell [HD]
  ✓ Garage Cam (CONNECTED) - G4-Pro [HD]  
  ✗ Backyard Cam (DISCONNECTED) - G3-Instant [SD]

Camera distribution ENABLED: 3 cameras, strategy: adaptive, offset: 15s
Rate limit analysis: limit=10 req/sec, effective=8 req/sec, max_intervals=2, concurrent_limit=4
```

Legend:
- `✓` = Connected camera
- `✗` = Disconnected camera  
- `[HD]` = Supports high-quality snapshots
- `[SD]` = Standard quality only

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

### Rate Limit Issues

**System validation fails with rate limit warnings:**
```
⚠️  Rate limit risk: 20 req/sec > 10 req/sec
   Consider enabling camera distribution or reducing camera count
```

Solutions:
- Enable camera distribution: `FETCH_ENABLE_CAMERA_DISTRIBUTION: "true"`
- Increase distribution window: `FETCH_DISTRIBUTION_WINDOW_SECONDS: "120"`
- Use manual concurrent limits: `FETCH_CONCURRENT_LIMIT_MODE: "manual"`

**Getting 429 "Too Many Requests" errors:**
- Check rate limit headers in logs
- Reduce concurrent limit: `FETCH_CONCURRENT_LIMIT_MANUAL: "3"`
- Increase safety buffer: `RATE_LIMIT_SAFETY_BUFFER: "0.6"`

### Camera Issues

**Cameras not being captured:**
- Check camera selection mode and whitelist/blacklist settings
- Verify camera names match exactly (check logs for "Available cameras")
- Ensure cameras are connected and online in UniFi Protect

**Some cameras fail with "400 Bad Request":**
- This usually means the camera doesn't support high-quality snapshots
- The application will automatically detect this and use standard quality
- Check logs for `[HD]` vs `[SD]` indicators

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
- Enable camera distribution to spread requests over time
- Use longer capture intervals

**Slow video creation:**
- Increase `FFMPEG_CONCURRENT_CREATION` for more parallel jobs
- Use faster presets like "fast" or "veryfast"
- Consider using a higher CRF value for faster encoding

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

2. **Add rate limiting configuration:**
   ```yaml
   # New rate limiting features
   UNIFI_PROTECT_RATE_LIMIT: "10"
   RATE_LIMIT_SAFETY_BUFFER: "0.8"
   FETCH_CONCURRENT_LIMIT_MODE: "auto"
   FETCH_ENABLE_CAMERA_DISTRIBUTION: "auto"
   ```

3. **Simplify camera configuration:**
   ```yaml
   # Old complex camera config (remove this)
   # UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG: '[{"name":"cam-front","stream_id":"abc123","intervals":[60]}]'
   
   # New simple config (add these)
   CAMERA_SELECTION_MODE: "whitelist"
   CAMERA_WHITELIST: '["Front Door Cam"]'
   FETCH_INTERVALS: '[60]'
   ```

4. **Update environment variable names:**
   - Most variables have been simplified (remove `UNIFI_PROTECT_TIME_LAPSE_` prefix)
   - Check the environmental variables table above for current names

### Benefits of Migration

- **99% more reliable** - no more RTSP connection issues
- **Rate limit compliance** - automatically respects API limits
- **Simpler configuration** - no manual stream ID management
- **Better performance** - direct API calls instead of video stream processing  
- **Automatic discovery** - finds cameras automatically
- **Smart quality** - uses best quality each camera supports
- **Better error handling** - comprehensive retry and recovery logic
- **System validation** - warns about configuration issues before they cause problems

## Support and Resources

- **Repository**: https://github.com/lux4rd0/unifi_protect_time_lapse
- **Documentation**: https://labs.lux4rd0.com/applications/unifi-protect-time-lapse/
- **Docker Hub**: https://hub.docker.com/r/lux4rd0/unifi_protect_time_lapse

For issues and feature requests, please use the GitHub repository's issue tracker.
