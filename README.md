# Unifi Protect Time Lapse

A Docker-based solution for creating time-lapse videos from Unifi Protect cameras. This application fetches images from your Unifi Protect cameras at regular intervals and compiles them into high-quality time-lapse videos.

## Overview

Unifi Protect Time Lapse connects to your UniFi Protect system to capture camera snapshots at configurable intervals. These snapshots are then automatically compiled into time-lapse videos daily, giving you a condensed view of what happened throughout the day.

### Features

- **Multiple Capture Intervals**: Configure different capture frequencies (e.g., every 15 seconds, every minute) for different cameras
- **Interval Optimization**: Automatically copy images between intervals to reduce camera load and network traffic
- **Detailed Status Summaries**: Get regular summaries showing success rates and performance for each camera
- **High-Quality Image Capture**: Uses RTSPS streams and FFMPEG to capture high-quality PNG images
- **Configurable Video Quality**: Choose between different video quality presets or create your own custom settings
- **Flexible Scheduling**: Set when time-lapses are created
- **Docker-Based**: Easy deployment using Docker

## Getting Started

### Prerequisites

- Docker and Docker Compose
- UniFi Protect system with accessible RTSP streams
- Stream IDs for your cameras (instructions below)

### Finding Your Camera Stream IDs

1. Log in to your UniFi Protect system
2. For each camera, go to its advanced settings page
3. Enable RTSP streaming if not already enabled
4. Note the RTSP URL which will be in the format: `rtsps://[ip-address]:7441/[stream-id]?enableSrtp`
5. The last part of the URL is your stream ID

### Deployment

1. Create a `compose.yml` file:

```yaml
services:
  unifi_protect_time_lapse:
    container_name: unifi_protect_time_lapse
    image: lux4rd0/unifi_protect_time_lapse:latest
    restart: always
    volumes:
      - ./output:/app/unifi_protect_time_lapse/output:rw
    environment:
      TZ: America/Chicago
      UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST: your-protect-host.example.com
      UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT: '7441'
      UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG: '[{"name":"cam-frontdoor","stream_id":"YOUR_STREAM_ID1","intervals":[15,60]},{"name":"cam-backyard","stream_id":"YOUR_STREAM_ID2","intervals":[60]}]'
      UNIFI_PROTECT_TIME_LAPSE_VIDEO_QUALITY_PRESET: 'high'
      UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE: 'iframe'
      
      # Enable optimizations and summaries
      UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING: 'true'
      UNIFI_PROTECT_TIME_LAPSE_HOURLY_SUMMARY_ENABLED: 'true'
      UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS: '3600'
      
      # Registry coordination settings
      UNIFI_PROTECT_TIME_LAPSE_REGISTRY_WINDOW: '7200'  # 2 hours registry retention
      UNIFI_PROTECT_TIME_LAPSE_WAIT_TIMEOUT: '20'       # 20 seconds max wait for source capture
```

2. Replace `your-protect-host.example.com` with your Protect system's hostname
3. Replace `YOUR_STREAM_ID1`, `YOUR_STREAM_ID2`, etc. with your actual camera stream IDs
4. Run `docker compose up -d`

## Environmental Variables

### Core Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST` | Hostname of your UniFi Protect system | - | `unifi.example.com` |
| `UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT` | RTSPS port for your UniFi Protect system | `7441` | `7441` |
| `UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG` | JSON array of camera configurations | - | See below |
| `UNIFI_PROTECT_TIME_LAPSE_DAYS_AGO` | Number of days ago to process for time-lapse creation | `1` | `0` |
| `UNIFI_PROTECT_TIME_LAPSE_CREATION_TIME` | Time of day to create time-lapses (24-hour format) | `01:00` | `03:30` |

**Note**: Fetch intervals are no longer configured using a separate environment variable. Instead, they are automatically derived from the `intervals` array specified for each camera in the `UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG`.

### Camera Configuration JSON

The `UNIFI_PROTECT_TIME_LAPSE_CAMERAS_CONFIG` variable takes a JSON array of camera objects. Each camera object has the following properties:

- `name`: A unique identifier for the camera (used for file naming)
- `stream_id`: The UniFi Protect stream ID for the camera
- `intervals`: An array of intervals (in seconds) to capture images for this camera

Example:
```json
[
  {"name":"cam-frontdoor","stream_id":"abcdefghijk123456","intervals":[15,60]},
  {"name":"cam-backyard","stream_id":"xyz987654321abcdef","intervals":[60]}
]
```

### Optimization and Summary Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING` | Enable automatic copying between intervals | `true` | `false` |
| `UNIFI_PROTECT_TIME_LAPSE_REGISTRY_WINDOW` | Duration in seconds to keep capture registry entries | `7200` | `3600` |
| `UNIFI_PROTECT_TIME_LAPSE_WAIT_TIMEOUT` | Maximum seconds to wait for source capture before falling back | `20` | `30` |
| `UNIFI_PROTECT_TIME_LAPSE_HOURLY_SUMMARY_ENABLED` | Enable periodic summary logs | `true` | `false` |
| `UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS` | Seconds between summary logs | `3600` | `1800` |

### Video Quality Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_TIME_LAPSE_VIDEO_QUALITY_PRESET` | Video quality preset (`medium`, `high`, or `custom`) | `medium` | `high` |
| `UNIFI_PROTECT_TIME_LAPSE_CUSTOM_CRF` | Custom Constant Rate Factor (lower = higher quality, 0-51) | `23` | `18` |
| `UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PRESET` | Custom encoding preset (ultrafast to veryslow) | `medium` | `slow` |
| `UNIFI_PROTECT_TIME_LAPSE_CUSTOM_PIX_FMT` | Custom pixel format | `yuv420p` | `yuv444p` |
| `UNIFI_PROTECT_TIME_LAPSE_CUSTOM_COLOR_SETTINGS` | Use explicit color space settings | `false` | `true` |

### Capture Technique Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE` | Frame capture technique (`standard`, `iframe`, or `blend`) | `standard` | `iframe` |
| `UNIFI_PROTECT_TIME_LAPSE_IFRAME_TIMEOUT` | Maximum time to wait for an I-frame in seconds (only used with `iframe` technique) | `2.0` | `3.0` |
| `UNIFI_PROTECT_TIME_LAPSE_BLEND_FRAMES` | Number of frames to blend together (only used with `blend` technique) | `2` | `3` |

### Path Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_TIME_LAPSE_IMAGE_OUTPUT_PATH` | Directory for storing captured images | `output/images` | `output/images` |
| `UNIFI_PROTECT_TIME_LAPSE_VIDEO_OUTPUT_PATH` | Directory for storing generated videos | `output/videos` | `output/videos` |

### Advanced Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_PROTECT_TIME_LAPSE_FETCH_TOP_OF_THE_MINUTE` | Align captures to the top of the minute | `true` | `false` |
| `UNIFI_PROTECT_TIME_LAPSE_TIMEOUT_PERCENTAGE` | Percentage of interval to use as timeout | `0.8` | `0.9` |
| `UNIFI_PROTECT_TIME_LAPSE_FFMPEG_FRAME_RATE` | Frame rate for generated videos | `30` | `24` |
| `UNIFI_PROTECT_TIME_LAPSE_FFMPEG_DELETE_IMAGES_AFTER_SUCCESS` | Delete images after successful video creation | `false` | `true` |
| `UNIFI_PROTECT_TIME_LAPSE_LOGGING_LEVEL` | Logging verbosity level | `INFO` | `DEBUG` |

## Docker Volume Structure

Images and videos are stored in the following structure:

```
output/
├── images/
│   ├── cam-frontdoor/
│   │   ├── 15s/
│   │   │   └── YYYY/MM/DD/
│   │   │       └── cam-frontdoor_1234567890.png
│   │   └── 60s/
│   │       └── YYYY/MM/DD/
│   └── cam-backyard/
│       └── ...
└── video/
    ├── YYYY/
    │   └── MM/
    │       ├── cam-frontdoor/
    │       │   ├── 15s/
    │       │   │   └── cam-frontdoor_YYYYMMDD_15s.mp4
    │       │   └── 60s/
    │       │       └── cam-frontdoor_YYYYMMDD_60s.mp4
    │       └── cam-backyard/
    │           └── ...
```

## Advanced Topics

### Smart Interval Optimization

When multiple intervals are configured for the same camera (e.g., 60s and 180s), the application can intelligently copy images between intervals instead of making redundant camera requests:

- For example, with intervals of 60s and 180s:
  - The 60s interval captures fresh images every minute
  - The 180s interval will use copies from the 60s interval (specifically the 1st, 4th, 7th images) rather than making separate requests
  
This provides several benefits:
- Reduces camera and network load
- Improves reliability
- Speeds up processing
- Maintains proper timing across all intervals

The system uses a coordinated approach where:
1. Smaller intervals register captures as they complete
2. Larger intervals explicitly wait for smaller interval captures to be ready
3. If a source capture isn't ready within a configurable timeout, it falls back to direct capture

This ensures files are never copied before they exist, eliminating "file not found" errors and providing maximum reliability.

The registry system is fully configurable through:
- `UNIFI_PROTECT_TIME_LAPSE_REGISTRY_WINDOW`: How long to maintain the capture registry (defaults to 2 hours)
- `UNIFI_PROTECT_TIME_LAPSE_WAIT_TIMEOUT`: Maximum time to wait for a source capture (defaults to 20 seconds)

For very long intervals (e.g., hours), you may need to increase the registry window to ensure proper coordination.

### Detailed Status Summaries

The application can provide detailed summaries at configurable intervals (default: hourly) showing:

- Overall success and failure rates
- Per-camera performance statistics
- Average fetch times for each camera
- Number of copied vs. freshly captured images when optimization is enabled

Example summary:
```
Summary for 60s interval (last 1 hour):
- Overall: 295 successful, 5 failed, 120 copied from other intervals
- cam-frontdoor: 60/60 successful (100.0%), 25 copied, avg time: 0.32s
- cam-backyard: 58/60 successful (96.7%), 20 copied, avg time: 0.45s
...
```

To adjust the frequency of summaries, change `UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS` (e.g., set to 1800 for 30-minute summaries).

### Quality Presets

The application offers three quality presets for video generation:

1. **medium** (default): Good balance between quality and file size
   - CRF: 25
   - Preset: medium
   - Pixel Format: yuv420p

2. **high**: Highest quality, larger file size
   - CRF: 18
   - Preset: slow
   - Pixel Format: yuv444p
   - Full color space settings

3. **custom**: Define your own settings using the custom environment variables

### Frame Capture Techniques

The application offers three techniques for capturing frames from RTSP streams:

1. **standard** (default): Captures a single frame directly from the stream
   - Simple and fast
   - May show motion blur in high-movement scenarios
   - Can produce corrupted or incomplete frames, especially with "Enhanced" encoding

2. **iframe**: Only captures I-frames (keyframes) from the stream
   - Higher quality images with less compression artifacts
   - Reduces motion blur in windy conditions
   - May take slightly longer to capture as it waits for an I-frame
   - Recommended for most Unifi Protect setups

3. **blend**: Blends multiple consecutive frames together
   - Reduces motion blur by averaging movement
   - Good for cameras mounted on unstable surfaces
   - Requires more processing time

Example configuration for a camera with high movement:

```yaml
UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE: 'iframe'
UNIFI_PROTECT_TIME_LAPSE_IFRAME_TIMEOUT: '2.0'
```

For very unstable cameras, the blend technique may work better:

```yaml
UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE: 'blend'
UNIFI_PROTECT_TIME_LAPSE_BLEND_FRAMES: '2'
```

### Unifi Protect Encoding Settings

Unifi Protect offers two encoding modes that can affect image capture quality:

1. **Enhanced**: Improves video quality while reducing storage size and optimizing streaming
   - Uses more aggressive compression with fewer I-frames
   - May cause issues with the `standard` capture technique
   - Recommended to use with the `iframe` capture technique

2. **Standard**: Improves playback compatibility for older devices
   - Uses less aggressive compression with more frequent I-frames
   - Works better with all capture techniques
   - May use more storage space on your Unifi Protect system

If you're experiencing blurry or corrupted images with the `standard` capture technique, consider either:
- Switching your cameras to "Standard" encoding mode in Unifi Protect settings, or
- Using the `iframe` capture technique in this application

### Multiple Site Deployment

To monitor multiple Protect sites, create separate Docker Compose configurations for each site:

```yaml
services:
  unifi_protect_time_lapse_site1:
    # Site 1 configuration...
    
  unifi_protect_time_lapse_site2:
    # Site 2 configuration...
```

## Troubleshooting

### No Images Being Captured

- Verify your Protect host is accessible
- Check that RTSP is enabled for your cameras
- Verify the stream IDs are correct
- Look at the container logs: `docker logs unifi_protect_time_lapse`

### Video Creation Fails

- Check that you have enough disk space
- Verify there are images available for the time period
- Check the container logs for FFMPEG errors

### RTSPS Connection Issues

- Verify your network allows connections to the RTSPS port
- Check that your Protect system has RTSP enabled
- Try increasing the timeout percentage

### Motion Blur or Corrupted Images

- If using "Enhanced" encoding mode in Unifi Protect, switch to the `iframe` capture technique
- For outdoor cameras subject to wind, use the `iframe` or `blend` techniques
- Consider switching problem cameras to "Standard" encoding mode in Unifi Protect
- For severe cases, increase the `UNIFI_PROTECT_TIME_LAPSE_IFRAME_TIMEOUT` to allow more time to find a good I-frame
- Check the container logs to verify which technique is being used

### Interval Optimization Issues

- If interval optimization is causing timing issues, verify that the intervals are proper multiples of each other
- For complex interval patterns, you may need to disable optimization by setting `UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING` to `false`
- Check the summary logs to see if images are being properly copied between intervals

### Registry Coordination Issues

- If larger intervals regularly fall back to direct capture with "waiting for source timed out" messages:
  - Increase `UNIFI_PROTECT_TIME_LAPSE_WAIT_TIMEOUT` to allow more time for smaller intervals to complete
  - Check that your server has sufficient resources to handle all camera captures within the wait timeout
  - Consider staggering your intervals more (e.g., use 60s and 300s instead of 60s and 180s)
- For very long intervals (hourly or longer):
  - Increase `UNIFI_PROTECT_TIME_LAPSE_REGISTRY_WINDOW` to at least 2x your longest interval
