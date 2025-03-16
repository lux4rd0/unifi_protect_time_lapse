# app/fetch_image.py

import os
import asyncio
import datetime
import logging
import config
import signal
import time
import shutil
from collections import defaultdict


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

        # Summary logging settings
        self.hourly_summary_enabled = (
            config.UNIFI_PROTECT_TIME_LAPSE_HOURLY_SUMMARY_ENABLED
        )
        self.summary_interval_seconds = (
            config.UNIFI_PROTECT_TIME_LAPSE_SUMMARY_INTERVAL_SECONDS
        )

        # Optimize interval fetching
        self.optimize_interval_fetching = (
            config.UNIFI_PROTECT_TIME_LAPSE_OPTIMIZE_INTERVAL_FETCHING
        )

        # Dictionary to store the last captured image path for each camera
        self.last_captured_images = {}

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

        if self.hourly_summary_enabled:
            logging.info(
                f"Summary logs enabled, interval: {self.summary_interval_seconds} seconds"
            )

        if self.optimize_interval_fetching:
            logging.info(
                "Interval optimization enabled: Images will be copied between intervals when possible"
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
            logging.debug(f"Created directory: {path}")
        return path

    async def fetch_camera_image(self, camera_name, image_path, interval):
        """
        Fetch an image from a Unifi Protect camera using ffmpeg.

        Args:
            camera_name: Name of the camera
            image_path: Path to save the image
            interval: Current interval in seconds

        Returns:
            tuple: (bool, float, str) - Success status, fetch time in seconds, and path to the image file
        """
        # Get camera RTSPS URL
        rtsps_url = config.UNIFI_PROTECT_TIME_LAPSE_get_camera_rtsps_url(camera_name)
        if not rtsps_url:
            logging.warning(
                f"No stream configuration for camera: {camera_name}. Skipping."
            )
            return False, 0.0, None

        # Check if we can copy from another interval instead of fetching
        if self.optimize_interval_fetching and camera_name in self.last_captured_images:
            last_image_info = self.last_captured_images[camera_name]
            # Only reuse images captured within the last interval seconds
            time_since_last_capture = time.time() - last_image_info["timestamp"]

            # If the last capture was recent enough (within this interval) and was successful
            if time_since_last_capture < interval and last_image_info["success"]:
                source_path = last_image_info["path"]
                if os.path.exists(source_path):
                    new_timestamp = int(datetime.datetime.now().timestamp())
                    new_filename = f"{camera_name}_{new_timestamp}.png"
                    dest_path = os.path.join(image_path, new_filename)

                    try:
                        start_time = time.time()
                        shutil.copy2(source_path, dest_path)
                        copy_time = time.time() - start_time

                        logging.debug(
                            f"{interval}s: Copied image for {camera_name} in {copy_time:.2f}s "
                            f"(reused from {last_image_info['interval']}s interval)"
                        )
                        return True, copy_time, dest_path
                    except Exception as e:
                        logging.error(f"Error copying image for {camera_name}: {e}")
                        # Fall through to regular fetch

        fetch_start = time.time()
        timestamp = int(datetime.datetime.now().timestamp())
        filename = f"{camera_name}_{timestamp}.png"
        filepath = os.path.join(image_path, filename)

        # Get timeout for this interval
        timeout = self.interval_timeouts[interval]

        # Base ffmpeg command
        ffmpeg_command = [
            "ffmpeg",
            "-rtsp_transport",
            "tcp",  # Use TCP for RTSP transport
            "-i",
            rtsps_url,
        ]

        # Add capture technique specific arguments
        ffmpeg_command.extend(
            config.UNIFI_PROTECT_TIME_LAPSE_ACTIVE_TECHNIQUE["ffmpeg_extra_args"]
        )

        # Add output arguments
        ffmpeg_command.extend(
            [
                "-frames:v",
                "1",
                "-f",
                "image2",
                "-pix_fmt",
                "rgb24",
                "-compression_level",
                "1",
                filepath,
                "-y",
            ]
        )

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
                        # Log which capture technique was used
                        technique_name = (
                            config.UNIFI_PROTECT_TIME_LAPSE_CAPTURE_TECHNIQUE
                        )
                        logging.debug(
                            f"{interval}s: Captured image from {camera_name} in {fetch_time:.2f}s using {technique_name} technique"
                        )

                        # Store this successful capture for potential reuse
                        self.last_captured_images[camera_name] = {
                            "path": filepath,
                            "timestamp": time.time(),
                            "success": True,
                            "interval": interval,
                        }

                        return True, fetch_time, filepath
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
                logging.warning(f"Fetch task for {camera_name} was cancelled.")
                return False, 0.0, None  # Exit the function cleanly
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
                    logging.warning(
                        f"Sleep interrupted for {camera_name} due to cancellation."
                    )
                    break  # Break the loop to stop further retries

        # Update the last captured image info to record failure
        self.last_captured_images[camera_name] = {
            "path": None,
            "timestamp": time.time(),
            "success": False,
            "interval": interval,
        }

        return False, 0.0, None

    async def run(self):
        # Sort intervals in ascending order for optimization
        sorted_intervals = sorted(self.intervals)

        # Create and start interval tasks in order (smallest intervals first)
        for interval in sorted_intervals:
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

        logging.debug(
            f"{interval}s: First fetch scheduled at {next_execution_time.strftime('%H:%M:%S')}"
        )

        # For detailed camera statistics
        last_summary_time = datetime.datetime.now()
        camera_stats = {
            camera: {
                "success": 0,
                "failure": 0,
                "total_time": 0.0,
                "fetches": 0,
                "copied": 0,
            }
            for camera in cameras
        }

        while True:
            now = datetime.datetime.now()

            # Check if it's time for the next fetch
            if now >= next_execution_time:
                # Log the execution time
                logging.debug(
                    f"{interval}s: Fetching {len(cameras)} cameras at {now.strftime('%H:%M:%S')}"
                )

                # Schedule next execution
                next_execution_time += datetime.timedelta(seconds=interval)
                logging.debug(
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
                    tasks.append((camera_name, task))

                if tasks:
                    # Execute all camera fetches concurrently and update statistics
                    for camera_name, task in tasks:
                        try:
                            success, fetch_time, image_path = await task
                            if success:
                                camera_stats[camera_name]["success"] += 1
                                camera_stats[camera_name]["total_time"] += fetch_time
                                camera_stats[camera_name]["fetches"] += 1

                                # Check if this was a copy operation
                                if (
                                    camera_name in self.last_captured_images
                                    and self.last_captured_images[camera_name]["path"]
                                    != image_path
                                ):
                                    camera_stats[camera_name]["copied"] += 1
                            else:
                                camera_stats[camera_name]["failure"] += 1
                        except Exception as e:
                            logging.error(
                                f"Unexpected error processing {camera_name}: {e}"
                            )
                            camera_stats[camera_name]["failure"] += 1

                # Check if it's time for summary and if summaries are enabled
                if (
                    self.hourly_summary_enabled
                    and (now - last_summary_time).total_seconds()
                    >= self.summary_interval_seconds
                ):
                    # Calculate overall statistics
                    total_success = sum(
                        stats["success"] for stats in camera_stats.values()
                    )
                    total_failure = sum(
                        stats["failure"] for stats in camera_stats.values()
                    )
                    total_copied = sum(
                        stats["copied"] for stats in camera_stats.values()
                    )

                    # Create detailed summary message
                    summary_time_period = (
                        f"{self.summary_interval_seconds // 60} minute"
                        if self.summary_interval_seconds < 3600
                        else f"{self.summary_interval_seconds // 3600} hour"
                    )
                    if summary_time_period.startswith("1 "):
                        summary_time_period += ""
                    else:
                        summary_time_period += "s"

                    summary_lines = [
                        f"Summary for {interval}s interval (last {summary_time_period}):"
                    ]
                    if self.optimize_interval_fetching:
                        summary_lines.append(
                            f"- Overall: {total_success} successful, {total_failure} failed, {total_copied} copied from other intervals"
                        )
                    else:
                        summary_lines.append(
                            f"- Overall: {total_success} successful, {total_failure} failed"
                        )

                    # Add per-camera statistics
                    for camera_name, stats in camera_stats.items():
                        if stats["fetches"] > 0:
                            avg_time = stats["total_time"] / stats["fetches"]
                            success_rate = (
                                (
                                    stats["success"]
                                    / (stats["success"] + stats["failure"])
                                )
                                * 100
                                if (stats["success"] + stats["failure"]) > 0
                                else 0
                            )

                            # Add copied info to the summary if optimization is enabled
                            if self.optimize_interval_fetching and stats["copied"] > 0:
                                summary_lines.append(
                                    f"- {camera_name}: {stats['success']}/{stats['success'] + stats['failure']} successful "
                                    f"({success_rate:.1f}%), {stats['copied']} copied, avg time: {avg_time:.2f}s"
                                )
                            else:
                                summary_lines.append(
                                    f"- {camera_name}: {stats['success']}/{stats['success'] + stats['failure']} successful "
                                    f"({success_rate:.1f}%), avg time: {avg_time:.2f}s"
                                )
                        else:
                            summary_lines.append(
                                f"- {camera_name}: No successful fetches"
                            )

                    # Log the summary as a multi-line message
                    logging.info("\n".join(summary_lines))

                    # Reset statistics and update last summary time
                    camera_stats = {
                        camera: {
                            "success": 0,
                            "failure": 0,
                            "total_time": 0.0,
                            "fetches": 0,
                            "copied": 0,
                        }
                        for camera in cameras
                    }
                    last_summary_time = now

            # Sleep until the next execution time
            sleep_time = (next_execution_time - datetime.datetime.now()).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    async def cleanup(self):
        logging.info("Cleanup completed.")
