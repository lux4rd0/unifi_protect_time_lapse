# app/main.py

import asyncio
from datetime import datetime, timedelta
from create_time_lapse import CreateTimeLapse
from fetch_image import FetchImage
import logging
import config
import platform
import os


# ASCII header for startup
def print_header():
    header = r"""
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

    # Get version from environment or use default
    version = os.environ.get("UNIFI_PROTECT_TIME_LAPSE_VERSION", "dev")
    build_date = os.environ.get("UNIFI_PROTECT_TIME_LAPSE_BUILD_DATE", "unknown")

    # Project information
    project_info = f"""
    Version: {version} (Built: {build_date})
    Created by: Dave Schmid (lux4rd0)
    Repository: https://github.com/lux4rd0/unifi_protect_time_lapse
    Documentation: https://labs.lux4rd0.com/applications/unifi-protect-time-lapse/
    Environment: {platform.system()} {platform.release()} {platform.machine()}
    Python: {platform.python_version()}
    """

    # Print header and project info
    logging.info("\n" + header)
    for line in project_info.strip().split("\n"):
        logging.info(line.strip())


async def run_timelapse_creation():
    while True:
        now = datetime.now()
        creation_time = datetime.strptime(
            config.UNIFI_PROTECT_TIME_LAPSE_CREATION_TIME, "%H:%M"
        )
        creation_hour, creation_minute = creation_time.hour, creation_time.minute

        # Calculate the next run time
        next_run_time = datetime(
            now.year, now.month, now.day, creation_hour, creation_minute
        )
        if now >= next_run_time:
            next_run_time += timedelta(days=1)

        # Log the scheduled run time
        logging.info(
            f"Time-lapse: Scheduled creation for {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}."
        )

        # Sleep until the next scheduled run time
        while True:
            now = datetime.now()
            if now >= next_run_time:
                break
            sleep_duration = (next_run_time - now).total_seconds()
            human_readable_sleep_duration = format_duration(sleep_duration)
            logging.info(
                f"Time-lapse: Sleeping until {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} (in {human_readable_sleep_duration})."
            )
            await asyncio.sleep(
                min(sleep_duration, 300)
            )  # Sleep in intervals of 5 minutes or less

        # Time to create timelapse
        start_time = datetime.now()
        logging.info(
            f"Time-lapse: Starting creation at {start_time.strftime('%Y-%m-%d %H:%M:%S')}..."
        )

        # Run timelapse creation
        time_lapse_creator = CreateTimeLapse()
        await time_lapse_creator.create_time_lapse_for_days_ago(
            config.UNIFI_PROTECT_TIME_LAPSE_DAYS_AGO
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        human_readable_duration = format_duration(duration)
        logging.info(
            f"Time-lapse: Creation completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')} in {human_readable_duration}."
        )

        # Update next_run_time for the next day
        next_run_time += timedelta(days=1)


def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


async def keep_alive():
    while True:
        await asyncio.sleep(1)  # Sleep for a short duration to keep the loop active


async def main():
    logging.basicConfig(
        level=config.UNIFI_PROTECT_TIME_LAPSE_LOGGING_LEVEL,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    logging.info("Starting Unifi Protect Time-lapse Service")

    # Print ASCII header and project information
    print_header()

    # Print configuration summary
    logging.info("==================== CONFIGURATION SUMMARY ====================")
    logging.info(
        f"Host: {config.UNIFI_PROTECT_TIME_LAPSE_PROTECT_HOST}:{config.UNIFI_PROTECT_TIME_LAPSE_PROTECT_PORT}"
    )
    logging.info(
        f"Configured Cameras: {len(config.UNIFI_PROTECT_TIME_LAPSE_CAMERA_NAMES)}"
    )
    logging.info(
        f"Intervals: {', '.join(str(i) for i in config.UNIFI_PROTECT_TIME_LAPSE_FETCH_INTERVALS)}"
    )
    logging.info(
        f"Video Creation Time: {config.UNIFI_PROTECT_TIME_LAPSE_CREATION_TIME}"
    )
    logging.info(
        f"Capture Technique: {config.UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE}"
    )
    logging.info(
        f"Video Quality: {config.UNIFI_PROTECT_TIME_LAPSE_VIDEO_QUALITY_PRESET}"
    )

    if config.UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING:
        logging.info(
            "Interval Optimization: Enabled - will copy between intervals when possible"
        )
    else:
        logging.info("Interval Optimization: Disabled")

    if config.UNIFI_PROTECT_TIME_LAPSE_HOURLY_SUMMARY_ENABLED:
        logging.info(
            f"Summary Logs: Enabled ({config.UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS//60} minute intervals)"
        )
    else:
        logging.info("Summary Logs: Disabled")

    logging.info("===============================================================")

    tasks = []

    # Start image fetching in background if enabled
    if config.UNIFI_PROTECT_TIME_LAPSE_FETCH_IMAGE_ENABLED:
        fetcher = FetchImage()
        image_fetch_task = asyncio.create_task(fetcher.run())
        tasks.append(image_fetch_task)
        logging.info("Fetch Image: Task is enabled and started.")
    else:
        logging.info("Fetch Image: Task is disabled and will not start.")

    # Schedule timelapse creation if enabled
    if config.UNIFI_PROTECT_TIME_LAPSE_CREATE_TIMELAPSE_ENABLED:
        timelapse_creation_task = asyncio.create_task(run_timelapse_creation())
        tasks.append(timelapse_creation_task)
        logging.info("Time-lapse: Creation task is enabled and scheduled.")
    else:
        logging.info("Time-lapse: Creation task is disabled and will not start.")

    # Include keep_alive task to ensure the loop runs indefinitely
    tasks.append(asyncio.create_task(keep_alive()))

    # Await all tasks
    await asyncio.gather(*tasks, return_exceptions=True)

    logging.info("Unifi Time-lapse Service stopped.")


if __name__ == "__main__":
    asyncio.run(main())
