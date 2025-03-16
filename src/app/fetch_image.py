# app/fetch_image.py

import os
import asyncio
import datetime
import logging
import config
import signal
import time


# Configuring logging
logging.basicConfig(
    level=config.UNIFI_PROTECT_TIME_LAPSE_LOGGING_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


class FetchImage:
    def __init__(self):
        self.image_output_path = config.UNIFI_PROTECT_TIME_LAPSE_IMAGE_OUTPUT_PATH
        self.intervals = config.UNIFI_PROTECT_TIME_LAPSE_FETCH_INTERVALS
        self.interval_timeouts = config.UNIFI_PROTECT_TIME_LAPSE_INTERVAL_TIMEOUTS
        self.cameras_by_interval = config.UNIFI_PROTECT_TIME_LAPSE_CAMERAS_BY_INTERVAL
        self.max_retries = config.UNIFI_PROTECT_TIME_LAPSE_FETCH_MAX_RETRIES
        self.retry_delay = config.UNIFI_PROTECT_TIME_LAPSE_FETCH_RETRY_DELAY

        # Log configuration summary
        logging.info(
            f"Configured intervals: {', '.join(str(interval) for interval in self.intervals)}"
        )
        logging.info(
            f"Timeout settings: {', '.join(f'{interval}s:{timeout}s' for interval, timeout in self.interval_timeouts.items())}"
        )

        for interval in self.intervals:
            cameras = self.cameras_by_interval[interval]
            logging.info(
                f"{interval}s interval: {len(cameras)} cameras: {', '.join(cameras)}"
            )

    async def create_directory_structure(self, camera_name, interval):
        """Create directory structure for storing images with given interval."""
        today = datetime.datetime.now()
        year, month, day = (
            today.strftime("%Y"),
            today.strftime("%m"),
            today.strftime("%d"),
        )
        interval_str = f"{interval}s"
        path = os.path.join(
            self.image_output_path, camera_name, interval_str, year, month, day
        )
        if not os.path.exists(path):
            os.makedirs(path)
            logging.info(f"Created directory: {path}")
        return path

    async def fetch_camera_image(self, camera_name, image_path, interval):
        """
        Fetch an image from a Unifi Protect camera using ffmpeg.

        Args:
            camera_name: Name of the camera
            image_path: Path to save the image
            interval: Current interval in seconds

        Returns:
            bool: True if successful, False otherwise
        """
        # Get camera RTSPS URL
        rtsps_url = config.UNIFI_PROTECT_TIME_LAPSE_get_camera_rtsps_url(camera_name)
        if not rtsps_url:
            logging.warning(
                f"No stream configuration for camera: {camera_name}. Skipping."
            )
            return False

        fetch_start = time.time()
        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"{camera_name}_{timestamp}.png"
        filepath = os.path.join(image_path, filename)

        # Get timeout for this interval
        timeout = self.interval_timeouts[interval]

        # Configure ffmpeg for Unifi Protect's RTSPS stream
        ffmpeg_command = [
            "ffmpeg",
            "-rtsp_transport",
            "tcp",  # Use TCP for RTSP transport
            "-i",
            rtsps_url,
            "-frames:v",
            "1",  # Capture a single frame
            "-f",
            "image2",  # Output format is an image
            "-pix_fmt",
            "rgb24",  # Full RGB colorspace without subsampling
            "-compression_level",
            "1",  # Good balance of quality vs size for PNG
            filepath,  # Already has .png extension
            "-y",  # Overwrite output file if it exists
        ]

        attempt = 0
        while attempt <= self.max_retries:
            try:
                # Run ffmpeg with timeout
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_command,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,  # Capture stderr for debugging if needed
                )

                # Use wait_for to implement timeout
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=timeout
                    )
                    fetch_time = time.time() - fetch_start
                    if (
                        process.returncode == 0
                        and os.path.exists(filepath)
                        and os.path.getsize(filepath) > 0
                    ):
                        logging.info(
                            f"{interval}s: Captured image from {camera_name} in {fetch_time:.2f}s"
                        )
                        return True
                    else:
                        if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
                            logging.error(f"Empty image file created for {camera_name}")
                            try:
                                os.remove(filepath)  # Remove empty file
                            except:
                                pass
                        else:
                            error_msg = (
                                stderr.decode("utf-8", errors="ignore")
                                if stderr
                                else "Unknown error"
                            )
                            logging.error(
                                f"Capture failed for {camera_name} with return code: {process.returncode}"
                            )
                            logging.debug(
                                f"FFMPEG error: {error_msg[:200]}..."
                            )  # Log first 200 chars of error
                except asyncio.TimeoutError:
                    fetch_time = time.time() - fetch_start
                    # Kill the process if it times out
                    try:
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass
                    logging.error(
                        f"Capture for {camera_name} timed out after {fetch_time:.2f}s (timeout: {timeout}s)"
                    )

            except asyncio.CancelledError:
                logging.info(f"Fetch task for {camera_name} was cancelled.")
                return False  # Exit the function cleanly
            except Exception as e:
                fetch_time = time.time() - fetch_start
                logging.error(
                    f"Error capturing {camera_name} image (attempt {attempt + 1}): {e}"
                )

            attempt += 1  # Increment attempt counter
            if attempt <= self.max_retries:
                try:
                    await asyncio.sleep(self.retry_delay)
                except asyncio.CancelledError:
                    # Handle cancellation during the sleep period
                    logging.info(
                        f"Sleep interrupted for {camera_name} due to cancellation."
                    )
                    break  # Break the loop to stop further retries

        return False

    async def run(self):
        # Create and start interval tasks individually - each will handle its own timing
        for interval in self.intervals:
            asyncio.create_task(self.handle_interval(interval))

    async def handle_interval(self, interval):
        # Get cameras for this interval
        cameras = self.cameras_by_interval[interval]

        if not cameras:
            logging.warning(
                f"No cameras configured for {interval}s interval. Skipping."
            )
            return

        logging.info(f"Starting {interval}s interval task for {len(cameras)} cameras")

        # Calculate initial execution time aligned to the interval
        now = datetime.datetime.now()
        seconds_since_minute = now.second + now.microsecond / 1000000
        seconds_to_next = interval - (seconds_since_minute % interval)

        # If we need to align to the top of the minute and this is a multiple of 60
        if (
            config.UNIFI_PROTECT_TIME_LAPSE_FETCH_TOP_OF_THE_MINUTE
            and interval % 60 == 0
        ):
            # Align to the next minute boundary
            next_execution_time = now + datetime.timedelta(
                seconds=60 - now.second, microseconds=-now.microsecond
            )
        else:
            # Align to the next interval boundary
            next_execution_time = now + datetime.timedelta(
                seconds=seconds_to_next, microseconds=-now.microsecond
            )

        logging.info(
            f"{interval}s: First fetch scheduled at {next_execution_time.strftime('%H:%M:%S')}"
        )

        while True:
            now = datetime.datetime.now()

            # Check if it's time for the next fetch
            if now >= next_execution_time:
                # Log the execution time
                logging.info(
                    f"{interval}s: Fetching {len(cameras)} cameras at {now.strftime('%H:%M:%S')}"
                )

                # Schedule next execution
                next_execution_time += datetime.timedelta(seconds=interval)
                logging.info(
                    f"{interval}s: Next fetch at {next_execution_time.strftime('%H:%M:%S')}"
                )

                # Create all camera tasks at once for simultaneous execution
                tasks = []
                for camera_name in cameras:
                    image_path = await self.create_directory_structure(
                        camera_name, interval
                    )
                    task = asyncio.create_task(
                        self.fetch_camera_image(camera_name, image_path, interval)
                    )
                    tasks.append(task)

                if tasks:
                    # Execute all camera fetches concurrently
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Sleep until the next execution time
            sleep_time = (next_execution_time - datetime.datetime.now()).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    async def cleanup(self):
        logging.info("Cleanup completed.")
