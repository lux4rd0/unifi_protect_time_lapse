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

    # Reduce httpx verbosity - keep only WARNING and ERROR logs
    logging.getLogger("httpx").setLevel(logging.WARNING)


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
    """

    # Get version info from environment variables set during Docker build
    version = os.environ.get("UNIFI_PROTECT_TIME_LAPSE_VERSION", "dev")
    build_date = os.environ.get("UNIFI_PROTECT_TIME_LAPSE_BUILD_DATE", "unknown")

    # Use logging instead of print
    for line in banner.split("\n"):
        if line.strip():  # Only log non-empty lines
            logging.info(line)

    # Version and build information
    logging.info(f"Version: {version} | Build Date: {build_date}")
    logging.info("Created by: Dave Schmid (lux4rd0)")
    logging.info("Repository: https://github.com/lux4rd0/unifi_protect_time_lapse")

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

    # Rate limiting settings
    logging.info("=" * 50)
    logging.info("RATE LIMITING")
    logging.info("=" * 50)
    logging.info(f"UniFi Protect Rate Limit: {config.UNIFI_PROTECT_RATE_LIMIT} req/sec")
    logging.info(f"Safety Buffer: {int(config.RATE_LIMIT_SAFETY_BUFFER * 100)}%")
    logging.info(f"Effective Rate Limit: {config.EFFECTIVE_RATE_LIMIT} req/sec")

    # Concurrent limit settings
    if config.FETCH_CONCURRENT_LIMIT_MODE == "auto":
        logging.info("Concurrent Limit: Auto-calculated based on rate limits")
    else:
        logging.info(
            f"Concurrent Limit: Manual ({config.FETCH_CONCURRENT_LIMIT_MANUAL})"
        )

    # Camera settings
    logging.info("=" * 50)
    logging.info("CAMERA SETTINGS")
    logging.info("=" * 50)
    logging.info(f"Camera Selection: {config.CAMERA_SELECTION_MODE}")
    if config.CAMERA_SELECTION_MODE == "whitelist" and config.CAMERA_WHITELIST:
        logging.info(f"Whitelisted Cameras: {', '.join(config.CAMERA_WHITELIST)}")
    elif config.CAMERA_SELECTION_MODE == "blacklist" and config.CAMERA_BLACKLIST:
        logging.info(f"Blacklisted Cameras: {', '.join(config.CAMERA_BLACKLIST)}")

    # Fetch settings
    logging.info("=" * 50)
    logging.info("FETCH SETTINGS")
    logging.info("=" * 50)
    logging.info(
        f"Fetch Intervals: {', '.join(f'{i}s' for i in config.FETCH_INTERVALS)}"
    )
    logging.info(f"Fetch Enabled: {config.FETCH_ENABLED}")
    logging.info(f"Top of Minute Alignment: {config.FETCH_TOP_OF_THE_MINUTE}")
    logging.info(f"Max Retries: {config.FETCH_MAX_RETRIES}")

    # Camera distribution settings
    logging.info("=" * 50)
    logging.info("CAMERA DISTRIBUTION")
    logging.info("=" * 50)
    logging.info(f"Distribution Mode: {config.FETCH_ENABLE_CAMERA_DISTRIBUTION}")
    logging.info(f"Distribution Strategy: {config.FETCH_DISTRIBUTION_STRATEGY}")

    if config.FETCH_ENABLE_CAMERA_DISTRIBUTION != "false":
        if config.FETCH_ENABLE_CAMERA_DISTRIBUTION == "auto":
            logging.info(
                f"Auto Threshold: ≥{config.FETCH_DISTRIBUTION_MIN_CAMERAS} cameras"
            )

        # Distribution parameters
        if config.FETCH_DISTRIBUTION_STRATEGY == "adaptive":
            logging.info(
                f"Adaptive Range: {config.FETCH_MIN_OFFSET_SECONDS}s - {config.FETCH_MAX_OFFSET_SECONDS}s"
            )
            logging.info(
                f"Distribution Window: {config.FETCH_DISTRIBUTION_WINDOW_SECONDS}s"
            )
        else:
            logging.info(f"Fixed Offset: {config.FETCH_CAMERA_OFFSET_SECONDS}s")

        logging.info(f"Log Slot Utilization: {config.FETCH_LOG_SLOT_UTILIZATION}")

    # Time-lapse settings
    logging.info("=" * 50)
    logging.info("TIME-LAPSE SETTINGS")
    logging.info("=" * 50)
    logging.info(f"Time-lapse Creation Enabled: {config.TIMELAPSE_CREATION_ENABLED}")
    logging.info(f"Creation Time: {config.TIMELAPSE_CREATION_TIME}")
    logging.info(f"Days Ago: {config.TIMELAPSE_DAYS_AGO}")

    # FFmpeg settings
    logging.info(f"Video Frame Rate: {config.FFMPEG_FRAME_RATE} fps")
    logging.info(f"Video Quality (CRF): {config.FFMPEG_CRF}")
    logging.info(f"FFmpeg Preset: {config.FFMPEG_PRESET}")
    logging.info(f"Concurrent Video Creation: {config.FFMPEG_CONCURRENT_CREATION}")

    # Paths
    logging.info("=" * 50)
    logging.info("PATHS")
    logging.info("=" * 50)
    logging.info(f"Image Output: {config.IMAGE_OUTPUT_PATH}")
    logging.info(f"Video Output: {config.VIDEO_OUTPUT_PATH}")

    # Logging
    logging.info("=" * 50)
    logging.info("LOGGING")
    logging.info("=" * 50)
    logging.info(f"Log Level: {config.LOGGING_LEVEL}")
    logging.info(f"Summary Reports: {config.SUMMARY_ENABLED}")
    if config.SUMMARY_ENABLED:
        logging.info(
            f"Summary Interval: {config.SUMMARY_INTERVAL_SECONDS // 60} minutes"
        )

    logging.info("=" * 80)


async def validate_system_capacity():
    """Validate that the system can handle the current configuration."""
    from camera_manager import CameraManager

    logging.info("Validating system capacity...")

    try:
        async with CameraManager() as camera_manager:
            # Get camera count
            cameras = await camera_manager.get_cameras(force_refresh=True)
            camera_count = len([cam for cam in cameras if cam.is_connected])

            if camera_count == 0:
                logging.warning(
                    "No connected cameras found - capacity validation skipped"
                )
                return True

            logging.info(f"Connected cameras: {camera_count}")

            # Calculate rate limit requirements
            max_simultaneous_intervals = config.calculate_max_simultaneous_intervals()
            effective_concurrent_limit = config.calculate_effective_concurrent_limit()

            logging.info(f"Max simultaneous intervals: {max_simultaneous_intervals}")
            logging.info(f"Effective concurrent limit: {effective_concurrent_limit}")

            # Validate rate limit compliance
            compliance = config.validate_rate_limit_compliance(camera_count)

            if not compliance:
                logging.error("❌ System configuration may exceed rate limits!")
                logging.error("Consider:")
                logging.error(
                    "  1. Enabling camera distribution (FETCH_ENABLE_CAMERA_DISTRIBUTION=auto)"
                )
                logging.error(
                    "  2. Reducing concurrent limit (FETCH_CONCURRENT_LIMIT_MODE=manual)"
                )
                logging.error(
                    "  3. Increasing distribution window (FETCH_DISTRIBUTION_WINDOW_SECONDS)"
                )
                return False
            else:
                logging.info("✅ System capacity validation passed")
                return True

    except Exception as e:
        logging.error(f"Error during capacity validation: {e}")
        return False


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

            # Use rate-limit aware capture method
            use_distribution = config.should_use_camera_distribution(len(cameras))
            if use_distribution:
                results = await camera_manager.capture_cameras_distributed(
                    timestamp, 60
                )
                method = "distributed"
            else:
                results = await camera_manager.capture_all_cameras(timestamp, 60)
                method = "concurrent"

            # Report results
            successful = sum(1 for success in results.values() if success)
            total = len(results)

            logging.info(
                f"Camera test completed ({method}): {successful}/{total} cameras accessible"
            )

            for camera_name, success in results.items():
                status = "✓" if success else "✗"
                logging.info(f"  {status} {camera_name}")

            # Report rate limit info
            max_simultaneous = config.calculate_max_simultaneous_intervals()
            concurrent_limit = config.calculate_effective_concurrent_limit()
            logging.info(
                f"Rate limit info: {concurrent_limit} concurrent, {max_simultaneous} max intervals"
            )

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

            # Validate system capacity before starting
            if not await validate_system_capacity():
                logging.error("System validation failed - aborting")
                sys.exit(1)

            logging.info("Starting fetch service only...")
            await run_fetch_only()
            return
        elif command in ["timelapse", "video"]:
            print_banner()
            print_configuration()
            logging.info("Starting time-lapse service only...")
            await run_timelapse_only()
            return
        elif command == "validate":
            print_banner()
            logging.info("Running system capacity validation...")
            success = await validate_system_capacity()
            if success:
                logging.info("✅ System validation passed")
            else:
                logging.error("❌ System validation failed")
                sys.exit(1)
            return
        elif command in ["help", "-h", "--help"]:
            logging.info("UniFi Protect Time-lapse Application")
            logging.info("")
            logging.info("Usage: python main.py [command]")
            logging.info("")
            logging.info("Commands:")
            logging.info("  (no args)  - Run both fetch and time-lapse services")
            logging.info("  test       - Test camera connectivity and exit")
            logging.info("  validate   - Validate system capacity and exit")
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

    # Validate system capacity
    if not await validate_system_capacity():
        logging.error("System validation failed - aborting startup")
        sys.exit(1)

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
