# app/main.py

import asyncio
from datetime import datetime, timedelta
from create_time_lapse import CreateTimeLapse
from fetch_image import FetchImage
import logging
import config


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
