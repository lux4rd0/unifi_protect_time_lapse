# UniFi Protect Time-lapse

> **This project has moved to [LuxUPT](https://github.com/luxardolabs/luxupt)** — a complete rewrite with a web interface, real-time monitoring, and much more.

---

## What Changed

This CLI-only tool has been replaced by **LuxUPT** (Lux UniFi Protect Timelapse), a full-featured application with:

- **Web UI** — Dashboard, camera management, image browser, timelapse viewer, and system settings — all from your browser
- **RTSP + API capture** — Choose per-camera between API snapshots and RTSP stream capture for the best resolution
- **Automatic scheduling** — Daily timelapse creation with configurable cameras, intervals, and encoding settings
- **Job system** — Create timelapses on-demand with real-time progress tracking
- **Live statistics** — Capture success rates, duration charts, and per-camera performance metrics
- **Multi-site support** — Run multiple instances for different UniFi Protect systems

Everything from the original — rate limiting, camera distribution, automatic discovery — is still there, now managed through the UI instead of environment variables.

## Quick Start

```yaml
services:
  luxupt:
    image: ghcr.io/luxardolabs/luxupt:latest
    container_name: luxupt
    restart: always
    ports:
      - "8080:8080"
    volumes:
      - ./output:/app/luxupt/output
    environment:
      TZ: America/Chicago
```

```bash
docker compose up -d
```

Open `http://your-server:8080` and follow the setup wizard.

## Links

- **New repo**: [github.com/luxardolabs/luxupt](https://github.com/luxardolabs/luxupt)
- **Documentation**: [Getting Started](https://github.com/luxardolabs/luxupt/blob/main/docs/getting-started.md)
- **Issues**: [github.com/luxardolabs/luxupt/issues](https://github.com/luxardolabs/luxupt/issues)

---

*This repository is archived and no longer maintained.*
