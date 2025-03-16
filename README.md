# Unifi Protect Time Lapse

A Docker-based solution for creating time-lapse videos from Unifi Protect cameras. This application fetches images from your Unifi Protect cameras at regular intervals and compiles them into high-quality time-lapse videos.

## Overview

Unifi Protect Time Lapse connects to your UniFi Protect system to capture camera snapshots at configurable intervals. These snapshots are then automatically compiled into time-lapse videos daily, giving you a condensed view of what happened throughout the day.

### Features

- **Multiple Capture Intervals**: Configure different capture frequencies (e.g., every 15 seconds, every minute) for different cameras
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

1. Create a `docker-compose.yml` file:

```yaml
version: '3'

services:
  unifi_time_lapse:
    container_name: unifi_time_lapse
    image: lux4rd0/unifi_time_lapse:latest
    restart: always
    volumes:
      - ./output:/app/unifi_time_lapse/output:rw
    environment:
      TZ: America/Chicago
      UNIFI_TIME_LAPSE_PROTECT_HOST: your-protect-host.example.com
      UNIFI_TIME_LAPSE_PROTECT_PORT: '7441'
      UNIFI_TIME_LAPSE_CAMERAS_CONFIG: '[{"name":"cam-frontdoor","stream_id":"YOUR_STREAM_ID1","intervals":[15,60]},{"name":"cam-backyard","stream_id":"YOUR_STREAM_ID2","intervals":[60]}]'
      UNIFI_TIME_LAPSE_VIDEO_QUALITY_PRESET: 'high'
```

2. Replace `your-protect-host.example.com` with your Protect system's hostname
3. Replace `YOUR_STREAM_ID1`, `YOUR_STREAM_ID2`, etc. with your actual camera stream IDs
4. Run `docker-compose up -d`

## Environmental Variables

### Core Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_TIME_LAPSE_PROTECT_HOST` | Hostname of your UniFi Protect system | - | `unifi.example.com` |
| `UNIFI_TIME_LAPSE_PROTECT_PORT` | RTSPS port for your UniFi Protect system | `7441` | `7441` |
| `UNIFI_TIME_LAPSE_CAMERAS_CONFIG` | JSON array of camera configurations | - | See below |
| `UNIFI_TIME_LAPSE_FETCH_INTERVALS` | Comma-separated list of fetch intervals in seconds | `15,60` | `10,30,60` |
| `UNIFI_TIME_LAPSE_DAYS_AGO` | Number of days ago to process for time-lapse creation | `1` | `0` |
| `UNIFI_TIME_LAPSE_CREATION_TIME` | Time of day to create time-lapses (24-hour format) | `01:00` | `03:30` |

### Camera Configuration JSON

The `UNIFI_TIME_LAPSE_CAMERAS_CONFIG` variable takes a JSON array of camera objects. Each camera object has the following properties:

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

### Video Quality Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_TIME_LAPSE_VIDEO_QUALITY_PRESET` | Video quality preset (`medium`, `high`, or `custom`) | `medium` | `high` |
| `UNIFI_TIME_LAPSE_CUSTOM_CRF` | Custom Constant Rate Factor (lower = higher quality, 0-51) | `23` | `18` |
| `UNIFI_TIME_LAPSE_CUSTOM_PRESET` | Custom encoding preset (ultrafast to veryslow) | `medium` | `slow` |
| `UNIFI_TIME_LAPSE_CUSTOM_PIX_FMT` | Custom pixel format | `yuv420p` | `yuv444p` |
| `UNIFI_TIME_LAPSE_CUSTOM_COLOR_SETTINGS` | Use explicit color space settings | `false` | `true` |

### Path Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_TIME_LAPSE_IMAGE_OUTPUT_PATH` | Directory for storing captured images | `output/images` | `/data/images` |
| `UNIFI_TIME_LAPSE_VIDEO_OUTPUT_PATH` | Directory for storing generated videos | `output/videos` | `/data/video` |

### Advanced Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `UNIFI_TIME_LAPSE_FETCH_TOP_OF_THE_MINUTE` | Align captures to the top of the minute | `true` | `false` |
| `UNIFI_TIME_LAPSE_TIMEOUT_PERCENTAGE` | Percentage of interval to use as timeout | `0.8` | `0.9` |
| `UNIFI_TIME_LAPSE_FFMPEG_FRAME_RATE` | Frame rate for generated videos | `30` | `24` |
| `UNIFI_TIME_LAPSE_FFMPEG_DELETE_IMAGES_AFTER_SUCCESS` | Delete images after successful video creation | `false` | `true` |
| `UNIFI_TIME_LAPSE_LOGGING_LEVEL` | Logging verbosity level | `INFO` | `DEBUG` |

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

### Multiple Site Deployment

To monitor multiple Protect sites, create separate Docker Compose configurations for each site:

```yaml
services:
  unifi_time_lapse_site1:
    # Site 1 configuration...
    
  unifi_time_lapse_site2:
    # Site 2 configuration...
```

## Troubleshooting

### No Images Being Captured

- Verify your Protect host is accessible
- Check that RTSP is enabled for your cameras
- Verify the stream IDs are correct
- Look at the container logs: `docker logs unifi_time_lapse`

### Video Creation Fails

- Check that you have enough disk space
- Verify there are images available for the time period
- Check the container logs for FFMPEG errors

### RTSPS Connection Issues

- Verify your network allows connections to the RTSPS port
- Check that your Protect system has RTSP enabled
- Try increasing the timeout percentage
