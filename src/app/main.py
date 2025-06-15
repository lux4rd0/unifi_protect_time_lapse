# app/main.py

import asyncio
import logging
import os
import platform
import signal
import sys
from datetime import datetime

import config
from fetch_service import FetchService
from timelapse_service import TimelapseService


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.LOGGING_LEVEL),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_banner():
    """Print application banner with version information."""
    banner = """
    ██╗   ██╗███╗   ██╗██╗███████╗██╗    ██████╗ ██████╗  ██████╗ ████████╗███████╗ ██████╗████████╗
    ██║   ██║████╗  ██║██║██╔════╝██║    ██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝
    ██║   ██║██╔██╗ ██║██║█████╗  ██║    ██████╔╝██████╔╝██║   ██║   ██║   █████╗  ██║        ██║   
    ██║   ██║██║╚██╗██║██║██╔══╝  ██║    ██╔═══╝ ██╔══██╗██║   ██║   ██║   ██╔══╝  ██║        ██║   
    ╚██████╔╝██║ ╚████║██║██║     ██║    ██║     ██║  ██║╚██████╔╝   ██║   ███████╗╚██████╗   ██║   
     ╚═════╝ ╚═╝  ╚═══╝╚═╝╚═╝     ╚═╝    ╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝ ╚═════╝   ╚═╝   
                                                                                                      
    ████████╗██╗███╗   ███╗███████╗    ██╗      █████╗ ██████╗ ███████╗███████╗                      
    ╚══██╔══╝██║████╗ ████║██╔════╝    ██║     ██╔══██╗██╔══██╗██╔════╝██╔════╝                      
       ██║   ██║██╔████╔██║█████╗      ██║     ███████║██████╔╝███████╗█████╗                        
       ██║   ██║██║╚██╔╝██║██╔══╝      ██║     ██╔══██║██╔═══╝ ╚════██║██╔══╝                        
       ██║   ██║██║ ╚═╝ ██║███████╗    ███████╗██║  ██║██║     ███████║███████╗                      
       ╚═╝   ╚═╝╚═╝     ╚═╝╚══════╝    ╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚══════╝                      

    Version: 2.0.0 (API-based) | Created by: Dave Schmid (lux4rd0)
    Repository: https://github.com/lux4rd0/unifi_protect_time_lapse
    """

    # Use logging instead of print
    for line in banner.split("\n"):
        if line.strip():  # Only log non-empty lines
            logging.info(line)

    # System information
    logging.info(
        f"Platform: {platform.system()} {platform.release()} {platform.machine()}"
    )
    logging.info(f"Python: {platform.python_version()}")
    logging.info(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def print_configuration():
    """Print current configuration."""
    logging.info("=" * 80)
    logging.info("CONFIGURATION SUMMARY")
    logging.info("=" * 80)

    # API settings
    api_url_display = config.UNIFI_PROTECT_BASE_URL
    if len(api_url_display) > 50:
        api_url_display = api_url_display[:47] + "..."

    logging.info(f"API URL: {api_url_display}")
    logging.info(
        f"API Key: {'*' * 20}...{config.UNIFI_PROTECT_API_KEY[-4:] if len(config.UNIFI_PROTECT_API_KEY) > 4 else '****'}"
    )
    logging.info(f"SSL Verification: {config.UNIFI_PROTECT_VERIFY_SSL}")
    logging.info(f"Request Timeout: {config.UNIFI_PROTECT_REQUEST_TIMEOUT}s")
    logging.info(f"Camera Refresh Interval: {config.CAMERA_REFRESH_INTERVAL}s")
    logging.info(f"High Quality Snapshots: {config.SNAPSHOT_HIGH_QUALITY}")

    # Camera settings
    logging.info(f"Camera Selection: {config.CAMERA_SELECTION_MODE}")
    if config.CAMERA_SELECTION_MODE == "whitelist" and config.CAMERA_WHITELIST:
        logging.info(f"Whitelisted Cameras: {', '.join(config.CAMERA_WHITELIST)}")
    elif config.CAMERA_SELECTION_MODE == "blacklist" and config.CAMERA_BLACKLIST:
        logging.info(f"Blacklisted Cameras: {', '.join(config.CAMERA_BLACKLIST)}")

    # Fetch settings
    logging.info(
        f"Fetch Intervals: {', '.join(f'{i}s' for i in config.FETCH_INTERVALS)}"
    )
    logging.info(f"Fetch Enabled: {config.FETCH_ENABLED}")
    logging.info(f"Top of Minute Alignment: {config.FETCH_TOP_OF_THE_MINUTE}")
    logging.info(f"Max Concurrent Fetches: {config.FETCH_CONCURRENT_LIMIT}")
    logging.info(f"Max Retries: {config.FETCH_MAX_RETRIES}")

    # Time-lapse settings
    logging.info(f"Time-lapse Creation Enabled: {config.TIMELAPSE_CREATION_ENABLED}")
    logging.info(f"Creation Time: {config.TIMELAPSE_CREATION_TIME}")
    logging.info(f"Days Ago: {config.TIMELAPSE_DAYS_AGO}")

    # FFmpeg settings
    logging.info(f"Video Frame Rate: {config.FFMPEG_FRAME_RATE} fps")
    logging.info(f"Video Quality (CRF): {config.FFMPEG_CRF}")
    logging.info(f"FFmpeg Preset: {config.FFMPEG_PRESET}")
    logging.info(f"Concurrent Video Creation: {config.FFMPEG_CONCURRENT_CREATION}")

    # Paths
    logging.info(f"Image Output: {config.IMAGE_OUTPUT_PATH}")
    logging.info(f"Video Output: {config.VIDEO_OUTPUT_PATH}")

    # Logging
    logging.info(f"Log Level: {config.LOGGING_LEVEL}")
    logging.info(f"Summary Reports: {config.SUMMARY_ENABLED}")
    if config.SUMMARY_ENABLED:
        logging.info(
            f"Summary Interval: {config.SUMMARY_INTERVAL_SECONDS // 60} minutes"
        )

    logging.info("=" * 80)


async def signal_handler(sig, loop):
    """Handle shutdown signals gracefully."""
    logging.info(f"Received signal {sig.name}, initiating graceful shutdown...")

    # Cancel all running tasks except the current one
    current_task = asyncio.current_task()
    for task in asyncio.all_tasks(loop):
        if task != current_task:
            task.cancel()

    # Wait for tasks to finish
    await asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True)


async def run_fetch_only():
    """Run only the fetch service."""
    fetch_service = FetchService()

    try:
        await fetch_service.start()
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception as e:
        logging.error(f"Fetch service error: {e}")
    finally:
        await fetch_service.stop()


async def run_timelapse_only():
    """Run only the time-lapse service."""
    timelapse_service = TimelapseService()

    try:
        await timelapse_service.start()
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception as e:
        logging.error(f"Time-lapse service error: {e}")
    finally:
        await timelapse_service.stop()


async def run_both_services():
    """Run both fetch and time-lapse services."""
    fetch_service = FetchService()
    timelapse_service = TimelapseService()

    try:
        # Start both services concurrently
        await asyncio.gather(
            fetch_service.start(), timelapse_service.start(), return_exceptions=True
        )
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception as e:
        logging.error(f"Service error: {e}")
    finally:
        # Stop both services
        await asyncio.gather(
            fetch_service.stop(), timelapse_service.stop(), return_exceptions=True
        )


async def create_timelapse_now():
    """Create time-lapse videos immediately and exit."""
    timelapse_service = TimelapseService()

    try:
        await timelapse_service.create_timelapse_now()
        logging.info("Time-lapse creation completed")
    except Exception as e:
        logging.error(f"Error creating time-lapse: {e}")


async def test_cameras():
    """Test camera connectivity and exit."""
    from camera_manager import CameraManager

    async with CameraManager() as camera_manager:
        try:
            cameras = await camera_manager.get_cameras(force_refresh=True)

            if not cameras:
                logging.warning(
                    "No cameras found or no cameras match selection criteria"
                )
                return

            logging.info(f"Testing connectivity to {len(cameras)} cameras...")

            # Test each camera
            timestamp = int(datetime.now().timestamp())
            results = await camera_manager.capture_all_cameras(timestamp, 60)

            # Report results
            successful = sum(1 for success in results.values() if success)
            total = len(results)

            logging.info(
                f"Camera test completed: {successful}/{total} cameras accessible"
            )

            for camera_name, success in results.items():
                status = "✓" if success else "✗"
                logging.info(f"  {status} {camera_name}")

        except Exception as e:
            logging.error(f"Error testing cameras: {e}")


async def main():
    """Main application entry point."""
    setup_logging()

    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "test":
            print_banner()
            logging.info("Running camera connectivity test...")
            await test_cameras()
            return
        elif command == "create":
            print_banner()
            logging.info("Creating time-lapse videos now...")
            await create_timelapse_now()
            return
        elif command in ["fetch", "capture"]:
            print_banner()
            print_configuration()
            logging.info("Starting fetch service only...")
            await run_fetch_only()
            return
        elif command in ["timelapse", "video"]:
            print_banner()
            print_configuration()
            logging.info("Starting time-lapse service only...")
            await run_timelapse_only()
            return
        elif command in ["help", "-h", "--help"]:
            logging.info("UniFi Protect Time-lapse Application")
            logging.info("")
            logging.info("Usage: python main.py [command]")
            logging.info("")
            logging.info("Commands:")
            logging.info("  (no args)  - Run both fetch and time-lapse services")
            logging.info("  test       - Test camera connectivity and exit")
            logging.info("  create     - Create time-lapse videos now and exit")
            logging.info("  fetch      - Run only the image fetch service")
            logging.info("  timelapse  - Run only the time-lapse creation service")
            logging.info("  help       - Show this help message")
            return
        else:
            logging.error(f"Unknown command: {command}")
            logging.error("Use 'python main.py help' for usage information")
            return

    # Validate configuration
    config_errors = config.validate_config()
    if config_errors:
        logging.error("Configuration errors found:")
        for error in config_errors:
            logging.error(f"  - {error}")
        sys.exit(1)

    # Print banner and configuration
    print_banner()
    print_configuration()

    # Ensure output directories exist
    config.ensure_directories()

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    for sig in [signal.SIGTERM, signal.SIGINT]:
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(signal_handler(s, loop))
        )

    # Determine what services to run
    services_to_run = []
    if config.FETCH_ENABLED:
        services_to_run.append("fetch")
    if config.TIMELAPSE_CREATION_ENABLED:
        services_to_run.append("time-lapse")

    if not services_to_run:
        logging.warning(
            "No services enabled. Enable FETCH_ENABLED and/or TIMELAPSE_CREATION_ENABLED"
        )
        return

    logging.info(f"Starting services: {', '.join(services_to_run)}")

    # Run appropriate services
    if config.FETCH_ENABLED and config.TIMELAPSE_CREATION_ENABLED:
        await run_both_services()
    elif config.FETCH_ENABLED:
        await run_fetch_only()
    elif config.TIMELAPSE_CREATION_ENABLED:
        await run_timelapse_only()

    logging.info("Application shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)
