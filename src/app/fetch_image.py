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

        # Registry settings
        self.registry_window = config.UNIFI_PROTECT_TIME_LAPSE_REGISTRY_WINDOW
        self.wait_timeout = config.UNIFI_PROTECT_TIME_LAPSE_WAIT_TIMEOUT

        # Coordination system for interval captures
        # Format: {timestamp: {camera_name: {interval: {"path": filepath, "ready": True/False}}}}
        self.capture_registry = {}

        # Use locks to protect the registry during concurrent access
        self.registry_lock = asyncio.Lock()

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
            logging.info(
                f"Registry window: {self.registry_window} seconds, wait timeout: {self.wait_timeout} seconds"
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

    async def register_capture(
        self, timestamp, camera_name, interval, filepath, ready=False
    ):
        """
        Register a pending or completed capture in the coordination system.

        Args:
            timestamp: Unix timestamp for the capture
            camera_name: Name of the camera
            interval: Interval in seconds
            filepath: Path to the image file
            ready: Whether the capture is ready (True) or pending (False)
        """
        async with self.registry_lock:
            # Initialize the structure if needed
            if timestamp not in self.capture_registry:
                self.capture_registry[timestamp] = {}

            if camera_name not in self.capture_registry[timestamp]:
                self.capture_registry[timestamp][camera_name] = {}

            # Register this capture
            self.capture_registry[timestamp][camera_name][interval] = {
                "path": filepath,
                "ready": ready,
            }

            # Calculate registry window based on longest interval
            max_interval = max(self.intervals)
            window_seconds = max(self.registry_window, max_interval * 2)

            # Clean up old entries (keep entries within window)
            current_time = int(time.time())
            old_timestamps = [
                ts
                for ts in self.capture_registry.keys()
                if current_time - ts > window_seconds
            ]

            if old_timestamps:
                for ts in old_timestamps:
                    del self.capture_registry[ts]
                logging.debug(
                    f"Cleaned up {len(old_timestamps)} old registry entries older than {window_seconds} seconds"
                )

    async def wait_for_capture(self, timestamp, camera_name, source_interval):
        """
        Wait for a capture to be ready.

        Args:
            timestamp: Unix timestamp for the capture
            camera_name: Name of the camera
            source_interval: Source interval in seconds

        Returns:
            tuple: (bool, str) - Success status and path to the image file
        """
        wait_start = time.time()
        logging.debug(
            f"Waiting for {camera_name} capture at timestamp {timestamp} from {source_interval}s interval"
        )

        while (time.time() - wait_start) < self.wait_timeout:
            async with self.registry_lock:
                # Check if the capture is registered and ready
                if (
                    timestamp in self.capture_registry
                    and camera_name in self.capture_registry[timestamp]
                    and source_interval in self.capture_registry[timestamp][camera_name]
                    and self.capture_registry[timestamp][camera_name][source_interval][
                        "ready"
                    ]
                ):
                    # Capture is ready
                    filepath = self.capture_registry[timestamp][camera_name][
                        source_interval
                    ]["path"]
                    return True, filepath

            # Not ready yet, wait a bit
            await asyncio.sleep(0.5)

        # Timed out waiting
        logging.error(
            f"Timed out waiting for {camera_name} capture at timestamp {timestamp} from {source_interval}s interval"
        )
        return False, None

    async def capture_fresh_image(self, camera_name, filepath, interval, timestamp):
        """
        Capture a fresh image from the camera.

        Args:
            camera_name: Name of the camera
            filepath: Full path to save the image
            interval: Current interval in seconds
            timestamp: Unix timestamp for the capture

        Returns:
            bool: Success status
        """
        # Register this pending capture
        await self.register_capture(
            timestamp, camera_name, interval, filepath, ready=False
        )

        # Get camera RTSPS URL
        rtsps_url = config.UNIFI_PROTECT_TIME_LAPSE_get_camera_rtsps_url(camera_name)
        if not rtsps_url:
            logging.warning(
                f"No stream configuration for camera: {camera_name}. Skipping."
            )
            return False, 0.0

        fetch_start = time.time()

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

                        # Mark this capture as ready
                        await self.register_capture(
                            timestamp, camera_name, interval, filepath, ready=True
                        )

                        return True, fetch_time
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
                return False, 0.0  # Exit the function cleanly
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

        # If we get here, capture failed after all retries
        return False, 0.0

    async def copy_image(
        self, source_file, dest_file, camera_name, interval, timestamp, source_interval
    ):
        """
        Copy an image from source to destination.

        Args:
            source_file: Path to the source image
            dest_file: Path to the destination image
            camera_name: Name of the camera
            interval: Current interval in seconds
            timestamp: Unix timestamp for the capture
            source_interval: Source interval in seconds

        Returns:
            tuple: (bool, float) - Success status and processing time
        """
        start_time = time.time()

        try:
            # Verify source file exists
            if not os.path.exists(source_file):
                logging.error(f"Source file not found for copying: {source_file}")
                return False, 0.0

            # Make sure destination directory exists
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)

            # Perform the copy
            shutil.copy2(source_file, dest_file)
            copy_time = time.time() - start_time

            # Register this copied capture as ready
            await self.register_capture(
                timestamp, camera_name, interval, dest_file, ready=True
            )

            logging.debug(
                f"{interval}s: Copied image for {camera_name} in {copy_time:.2f}s "
                f"(reused from {source_interval}s interval)"
            )

            return True, copy_time

        except Exception as e:
            logging.error(f"Error copying image for {camera_name}: {e}")
            return False, 0.0

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
                # Store the current execution time
                current_execution = next_execution_time
                execution_timestamp = int(current_execution.timestamp())

                # Schedule next execution
                next_execution_time += datetime.timedelta(seconds=interval)

                # Log the execution
                logging.debug(
                    f"{interval}s: Fetching {len(cameras)} cameras at {current_execution.strftime('%H:%M:%S')}"
                )
                logging.debug(
                    f"{interval}s: Next fetch scheduled for {next_execution_time.strftime('%H:%M:%S')}"
                )

                # Determine if we should try to copy from smaller intervals
                use_copy_strategy = False
                source_interval = None

                if self.optimize_interval_fetching and interval > min(self.intervals):
                    # Find a suitable smaller interval to copy from
                    for smaller_interval in sorted(self.intervals):
                        # Skip if not smaller or doesn't divide evenly
                        if (
                            smaller_interval >= interval
                            or interval % smaller_interval != 0
                        ):
                            continue

                        # This is a candidate smaller interval
                        # Check if the current execution time aligns with this smaller interval
                        if execution_timestamp % smaller_interval == 0:
                            # Alignment confirmed - use this smaller interval
                            use_copy_strategy = True
                            source_interval = smaller_interval
                            logging.debug(
                                f"{interval}s: Will use images from {smaller_interval}s interval for this execution"
                            )
                            break

                # Process all cameras for this interval execution
                async def process_camera(
                    camera_name, use_copy=False, copy_from_interval=None
                ):
                    """Process a single camera for this interval execution"""
                    # Create directory for this camera
                    image_path = await self.create_directory_structure(
                        camera_name, interval
                    )

                    # Create the filename with the execution timestamp
                    filename = f"{camera_name}_{execution_timestamp}.png"
                    filepath = os.path.join(image_path, filename)

                    # Determine if we should copy for this specific camera
                    camera_use_copy = use_copy

                    # Skip copy if this camera isn't in the source interval
                    if camera_use_copy and copy_from_interval:
                        if camera_name not in self.cameras_by_interval.get(
                            copy_from_interval, []
                        ):
                            camera_use_copy = False
                            logging.debug(
                                f"{interval}s: Camera {camera_name} not in {copy_from_interval}s interval, will capture fresh"
                            )

                    if camera_use_copy and copy_from_interval:
                        # Wait for the source interval to capture this image first
                        source_year = current_execution.strftime("%Y")
                        source_month = current_execution.strftime("%m")
                        source_day = current_execution.strftime("%d")

                        source_path = os.path.join(
                            self.image_output_path,
                            camera_name,
                            f"{copy_from_interval}s",
                            source_year,
                            source_month,
                            source_day,
                            f"{camera_name}_{execution_timestamp}.png",
                        )

                        # Wait for the source capture to be ready
                        ready, source_file = await self.wait_for_capture(
                            execution_timestamp, camera_name, copy_from_interval
                        )

                        if ready:
                            # Source capture is ready, we can copy it
                            success, processing_time = await self.copy_image(
                                source_file,
                                filepath,
                                camera_name,
                                interval,
                                execution_timestamp,
                                copy_from_interval,
                            )

                            if success:
                                camera_stats[camera_name]["success"] += 1
                                camera_stats[camera_name][
                                    "total_time"
                                ] += processing_time
                                camera_stats[camera_name]["fetches"] += 1
                                camera_stats[camera_name]["copied"] += 1
                                return
                            else:
                                # Copy failed, fall back to direct capture
                                logging.warning(
                                    f"{interval}s: Copy failed for {camera_name}, falling back to direct capture"
                                )
                        else:
                            # Waiting for source timed out, fall back to direct capture
                            logging.warning(
                                f"{interval}s: Waiting for source timed out for {camera_name}, falling back to direct capture"
                            )

                    # Direct capture (either as primary strategy or fallback)
                    success, processing_time = await self.capture_fresh_image(
                        camera_name, filepath, interval, execution_timestamp
                    )

                    if success:
                        camera_stats[camera_name]["success"] += 1
                        camera_stats[camera_name]["total_time"] += processing_time
                        camera_stats[camera_name]["fetches"] += 1
                    else:
                        camera_stats[camera_name]["failure"] += 1

                # Process all cameras concurrently
                tasks = []
                for camera_name in cameras:
                    task = asyncio.create_task(
                        process_camera(camera_name, use_copy_strategy, source_interval)
                    )
                    tasks.append(task)

                # Wait for all cameras to be processed
                try:
                    await asyncio.gather(*tasks)
                except Exception as e:
                    logging.error(f"Error during camera processing: {e}")

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
