# app/timelapse_service.py

import asyncio
import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import time

import config
from camera_manager import CameraManager


class TimelapseService:
    """Service for creating time-lapse videos from captured images."""

    def __init__(self):
        self.camera_manager: CameraManager
        self.running = False
        self.creation_task: asyncio.Task[None] | None = None

        # Semaphore to limit concurrent video creation
        self.creation_semaphore = asyncio.Semaphore(config.FFMPEG_CONCURRENT_CREATION)

        logging.info(
            f"Time-lapse service initialized, creation time: {config.TIMELAPSE_CREATION_TIME}"
        )

    async def start(self):
        """Start the time-lapse service."""
        if self.running:
            logging.warning("Time-lapse service is already running")
            return

        self.running = True

        # Initialize camera manager
        self.camera_manager = CameraManager()
        await self.camera_manager.__aenter__()

        try:
            # Start creation task
            self.creation_task = asyncio.create_task(self._run_creation_loop())
            await self.creation_task

        finally:
            await self.stop()

    async def stop(self):
        """Stop the time-lapse service."""
        if not self.running:
            return

        self.running = False

        # Cancel creation task
        if self.creation_task and not self.creation_task.done():
            self.creation_task.cancel()
            try:
                await self.creation_task
            except asyncio.CancelledError:
                pass

        # Close camera manager
        if hasattr(self, "camera_manager"):
            await self.camera_manager.__aexit__(None, None, None)

        logging.info("Time-lapse service stopped")

    async def _run_creation_loop(self):
        """Run the time-lapse creation loop."""
        while self.running:
            now = datetime.now()

            # Parse creation time
            creation_time = datetime.strptime(config.TIMELAPSE_CREATION_TIME, "%H:%M")
            next_creation = now.replace(
                hour=creation_time.hour,
                minute=creation_time.minute,
                second=0,
                microsecond=0,
            )

            # If the time has passed today, schedule for tomorrow
            if now >= next_creation:
                next_creation += timedelta(days=1)

            # Calculate sleep time
            sleep_time = (next_creation - now).total_seconds()

            logging.info(
                f"Next time-lapse creation scheduled for {next_creation.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(in {sleep_time/3600:.1f} hours)"
            )

            # Sleep in chunks to allow for graceful shutdown
            while self.running and datetime.now() < next_creation:
                chunk_sleep = min(
                    config.MAX_SLEEP_INTERVAL,
                    (next_creation - datetime.now()).total_seconds(),
                )
                if chunk_sleep > 0:
                    await asyncio.sleep(chunk_sleep)

            if not self.running:
                break

            # Time to create time-lapses
            start_time = datetime.now()
            logging.info(
                f"Starting time-lapse creation at {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            try:
                await self._create_timelapses_for_date(
                    datetime.now() - timedelta(days=config.TIMELAPSE_DAYS_AGO)
                )
            except Exception as e:
                logging.error(f"Error during time-lapse creation: {e}")

            end_time = datetime.now()
            duration_seconds = (end_time - start_time).total_seconds()
            logging.info(
                f"Time-lapse creation completed in {self._format_duration(duration_seconds)}"
            )

    async def _create_timelapses_for_date(self, target_date: datetime):
        """Create time-lapses for a specific date."""
        # Get list of cameras
        cameras = await self.camera_manager.get_cameras()

        if not cameras:
            logging.warning("No cameras available for time-lapse creation")
            return

        date_str = target_date.strftime("%Y-%m-%d")
        logging.info(f"Creating time-lapses for {date_str} with {len(cameras)} cameras")

        # Create tasks for each camera and interval combination
        tasks = []
        for camera in cameras:
            for interval in config.FETCH_INTERVALS:
                task = asyncio.create_task(
                    self._create_timelapse_for_camera_interval(
                        camera.safe_name, interval, target_date
                    )
                )
                tasks.append(task)

        # Execute all creation tasks
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            successful = sum(1 for result in results if result is True)
            failed = sum(1 for result in results if isinstance(result, Exception))
            skipped = len(results) - successful - failed

            logging.info(
                f"Time-lapse creation summary: {successful} successful, {failed} failed, {skipped} skipped"
            )

    async def _create_timelapse_for_camera_interval(
        self, camera_name: str, interval: int, target_date: datetime
    ) -> bool | None:
        """Create a time-lapse video for a specific camera and interval."""

        async with self.creation_semaphore:
            year = target_date.strftime("%Y")
            month = target_date.strftime("%m")
            day = target_date.strftime("%d")

            # Define paths
            images_path = (
                config.IMAGE_OUTPUT_PATH
                / camera_name
                / f"{interval}s"
                / year
                / month
                / day
            )
            videos_path = (
                config.VIDEO_OUTPUT_PATH / year / month / camera_name / f"{interval}s"
            )

            # Check if images directory exists and has images
            if not images_path.exists():
                logging.debug(
                    f"No images directory for {camera_name} {interval}s on {target_date.strftime('%Y-%m-%d')}"
                )
                return None

            # Find image files
            image_files = list(images_path.glob(f"{camera_name}_*.jpg"))
            if not image_files:
                logging.debug(
                    f"No images found for {camera_name} {interval}s on {target_date.strftime('%Y-%m-%d')}"
                )
                return None

            logging.info(
                f"Creating time-lapse for {camera_name} {interval}s: {len(image_files)} images"
            )

            # Create output directory
            videos_path.mkdir(parents=True, exist_ok=True)

            # Define output file
            output_filename = f"{camera_name}_{year}{month}{day}_{interval}s.mp4"
            output_path = videos_path / output_filename

            # Check if file already exists and we shouldn't overwrite
            if output_path.exists() and not config.FFMPEG_OVERWRITE_FILE:
                logging.info(
                    f"Time-lapse already exists for {camera_name} {interval}s, skipping"
                )
                return None

            # Create time-lapse video
            success = await self._create_video(
                images_path, output_path, camera_name, interval
            )

            if success and config.FFMPEG_DELETE_IMAGES_AFTER_SUCCESS:
                try:
                    shutil.rmtree(images_path)
                    logging.info(
                        f"Deleted images for {camera_name} {interval}s after successful video creation"
                    )
                except Exception as e:
                    logging.error(
                        f"Failed to delete images for {camera_name} {interval}s: {e}"
                    )

            return success

    async def _create_video(
        self, images_path: Path, output_path: Path, camera_name: str, interval: int
    ) -> bool:
        """Create a video using FFmpeg."""

        start_time = time.time()

        # Build FFmpeg command
        input_pattern = str(images_path / f"{camera_name}_*.jpg")

        ffmpeg_command = [
            "ffmpeg",
            "-y" if config.FFMPEG_OVERWRITE_FILE else "-n",
            "-loglevel",
            "error",
            "-nostats",
            "-framerate",
            str(config.FFMPEG_FRAME_RATE),
            "-pattern_type",
            "glob",
            "-i",
            input_pattern,
            "-c:v",
            "libx264",
            "-preset",
            config.FFMPEG_PRESET,
            "-crf",
            str(config.FFMPEG_CRF),
            "-pix_fmt",
            config.FFMPEG_PIXEL_FORMAT,
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        logging.debug(f"FFmpeg command: {' '.join(ffmpeg_command)}")

        try:
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            end_time = time.time()
            duration_seconds = end_time - start_time

            if process.returncode == 0:
                # Verify output file
                if output_path.exists() and output_path.stat().st_size > 0:
                    file_size = output_path.stat().st_size
                    formatted_size = self._format_file_size(file_size)

                    logging.info(
                        f"✓ Created time-lapse for {camera_name} {interval}s in "
                        f"{self._format_duration(duration_seconds)}, size: {formatted_size}"
                    )
                    return True
                else:
                    logging.error(
                        f"✗ Output file not created or empty for {camera_name} {interval}s"
                    )
                    return False
            else:
                error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                logging.error(
                    f"✗ FFmpeg failed for {camera_name} {interval}s: {error_msg[:200]}"
                )
                return False

        except Exception as e:
            logging.error(f"✗ Error creating video for {camera_name} {interval}s: {e}")
            return False

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    async def create_timelapse_now(self, days_ago: int = 1) -> None:
        """
        Create time-lapses immediately for testing purposes.

        Args:
            days_ago: Number of days ago to create time-lapses for (default: from config)
        """
        target_date = datetime.now() - timedelta(days=days_ago)

        if not hasattr(self, "camera_manager"):
            self.camera_manager = CameraManager()
            await self.camera_manager.__aenter__()
            should_cleanup = True
        else:
            should_cleanup = False

        try:
            await self._create_timelapses_for_date(target_date)
        finally:
            if should_cleanup:
                await self.camera_manager.__aexit__(None, None, None)
                del self.camera_manager
