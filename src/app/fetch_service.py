# app/fetch_service.py

import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, cast
import time
import shutil
from pathlib import Path

import config
from camera_manager import CameraManager


class FetchService:
    """Service for periodically fetching camera snapshots."""

    def __init__(self):
        self.camera_manager: CameraManager
        self.interval_tasks: List[asyncio.Task] = []
        self.running = False

        # Statistics tracking
        self.stats = {
            interval: {
                "total_captures": 0,
                "successful_captures": 0,
                "failed_captures": 0,
                "reused_captures": 0,
                "last_capture_time": None,
                "camera_stats": defaultdict(
                    lambda: {"success": 0, "failure": 0, "reused": 0}
                ),
            }
            for interval in config.FETCH_INTERVALS
        }

        self.last_summary_time = datetime.now()

        logging.info(
            f"Fetch service initialized with intervals: {config.FETCH_INTERVALS}"
        )

        # Check for optimization opportunities
        sorted_intervals = sorted(config.FETCH_INTERVALS)
        for i, interval in enumerate(sorted_intervals):
            smaller_intervals = [x for x in sorted_intervals[:i] if interval % x == 0]
            if smaller_intervals:
                source = max(smaller_intervals)
                logging.info(
                    f"Interval optimization: {interval}s will reuse images from {source}s when aligned"
                )

    async def start(self):
        """Start the fetch service."""
        if self.running:
            logging.warning("Fetch service is already running")
            return

        self.running = True

        # Initialize camera manager
        self.camera_manager = CameraManager()
        await self.camera_manager.__aenter__()

        try:
            # Discover cameras initially
            await self.camera_manager.get_cameras(force_refresh=True)

            # Start interval tasks in order (smallest intervals first)
            sorted_intervals = sorted(config.FETCH_INTERVALS)
            for interval in sorted_intervals:
                task = asyncio.create_task(self._run_interval(interval))
                self.interval_tasks.append(task)
                logging.info(f"Started {interval}s interval task")

            # Start summary task if enabled
            if config.SUMMARY_ENABLED:
                summary_task = asyncio.create_task(self._run_summary())
                self.interval_tasks.append(summary_task)
                logging.info(
                    f"Started summary task ({config.SUMMARY_INTERVAL_SECONDS}s intervals)"
                )

            # Wait for all tasks
            await asyncio.gather(*self.interval_tasks, return_exceptions=True)

        finally:
            await self.stop()

    async def stop(self):
        """Stop the fetch service."""
        if not self.running:
            return

        self.running = False

        # Cancel all tasks
        for task in self.interval_tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.interval_tasks:
            await asyncio.gather(*self.interval_tasks, return_exceptions=True)

        # Close camera manager
        if hasattr(self, "camera_manager"):
            await self.camera_manager.__aexit__(None, None, None)

        logging.info("Fetch service stopped")

    async def _run_interval(self, interval: int):
        """Run capture loop for a specific interval."""
        logging.info(f"Starting {interval}s interval capture loop")

        # Calculate initial delay to align with interval
        now = datetime.now()
        current_timestamp = int(now.timestamp())

        # Find the next timestamp that aligns with this interval
        remainder = current_timestamp % interval
        if remainder == 0:
            # We're already aligned, use current time
            next_timestamp = current_timestamp
            next_execution = now
        else:
            # Calculate next aligned timestamp
            next_timestamp = current_timestamp + (interval - remainder)
            next_execution = datetime.fromtimestamp(next_timestamp)

        # For minute alignment preference on 60+ second intervals
        if config.FETCH_TOP_OF_THE_MINUTE and interval >= 60:
            # Ensure the timestamp also aligns with minute boundaries (ends in 0 seconds)
            while next_timestamp % 60 != 0:
                next_timestamp += interval
                next_execution = datetime.fromtimestamp(next_timestamp)

        # Verify final alignment
        if next_timestamp % interval != 0:
            logging.error(
                f"{interval}s: Alignment calculation failed! Timestamp {next_timestamp} not divisible by {interval}"
            )
            return

        # Wait for first execution
        sleep_time = (next_execution - datetime.now()).total_seconds()
        if sleep_time > 0:
            logging.info(
                f"{interval}s: First capture in {sleep_time:.1f}s at {next_execution.strftime('%H:%M:%S')} (timestamp: {next_timestamp})"
            )
            # Verify alignment will work for image reuse
            smaller_intervals = [
                i for i in config.FETCH_INTERVALS if i < interval and interval % i == 0
            ]
            if smaller_intervals:
                source_interval = max(smaller_intervals)
                if next_timestamp % source_interval == 0:
                    logging.info(
                        f"{interval}s: ✅ Will be able to reuse images from {source_interval}s interval"
                    )
                else:
                    logging.warning(
                        f"{interval}s: ⚠️  Will NOT align with {source_interval}s interval for image reuse"
                    )

            await asyncio.sleep(sleep_time)

        while self.running:
            capture_time = datetime.now()
            timestamp = int(capture_time.timestamp())

            # Verify we're still aligned (should always be true now)
            if timestamp % interval != 0:
                logging.warning(
                    f"{interval}s: Timestamp {timestamp} not aligned with interval, skipping"
                )
                await asyncio.sleep(1)
                continue

            try:
                # Try to reuse images from smaller intervals first
                reused_count = await self._try_reuse_images(interval, timestamp)

                if reused_count > 0:
                    # We successfully reused images
                    self._update_reuse_stats(interval, reused_count, capture_time)
                    logging.info(
                        f"{interval}s: Reused {reused_count} images from smaller intervals"
                    )
                else:
                    # Need to capture fresh images
                    logging.debug(f"{interval}s: No images reused, capturing fresh")
                    results = await self.camera_manager.capture_all_cameras(
                        timestamp, interval
                    )

                    # Update statistics
                    self._update_stats(interval, results, capture_time)

                    # Log interval summary
                    successful = sum(1 for success in results.values() if success)
                    total = len(results)
                    logging.debug(
                        f"{interval}s: Captured {successful}/{total} at {capture_time.strftime('%H:%M:%S')}"
                    )

            except Exception as e:
                logging.error(f"Error in {interval}s interval capture: {e}")
                self.stats[interval]["failed_captures"] += 1

            # Calculate next execution time (always maintain alignment)
            next_timestamp = timestamp + interval
            next_execution = datetime.fromtimestamp(next_timestamp)

            # Sleep until next execution
            sleep_time = (next_execution - datetime.now()).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            elif sleep_time < -interval / 2:
                # We're running significantly behind, log warning but continue
                logging.warning(
                    f"{interval}s interval is running {-sleep_time:.1f}s behind schedule"
                )
                # Don't reset schedule - just continue with next aligned timestamp

    async def _try_reuse_images(self, interval: int, timestamp: int) -> int:
        """Try to reuse images from smaller intervals instead of capturing fresh."""

        # Only try to reuse if this isn't the smallest interval
        smaller_intervals = [
            i for i in config.FETCH_INTERVALS if i < interval and interval % i == 0
        ]
        if not smaller_intervals:
            logging.debug(f"{interval}s: No smaller intervals available for reuse")
            return 0  # No smaller intervals to reuse from

        # Find the best source interval (largest smaller interval that divides evenly)
        source_interval = max(smaller_intervals)

        # Check if the timestamp aligns with the source interval
        if timestamp % source_interval != 0:
            logging.debug(
                f"{interval}s: Timestamp {timestamp} doesn't align with {source_interval}s interval (remainder: {timestamp % source_interval})"
            )
            return 0  # Timestamp doesn't align

        # Also check if timestamp aligns with the current interval
        if timestamp % interval != 0:
            logging.debug(
                f"{interval}s: Timestamp {timestamp} doesn't align with {interval}s interval (remainder: {timestamp % interval})"
            )
            return 0  # Current interval not aligned either

        logging.info(
            f"{interval}s: Attempting to reuse images from {source_interval}s interval at timestamp {timestamp}"
        )

        # Wait for source files to be written and flushed to disk (now configurable)
        await asyncio.sleep(config.FETCH_IMAGE_REUSE_DELAY)

        cameras = await self.camera_manager.get_cameras()
        connected_cameras = [camera for camera in cameras if camera.is_connected]

        reused_count = 0

        for camera in connected_cameras:
            # Build source and destination paths
            date_obj = datetime.fromtimestamp(timestamp)
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m")
            day = date_obj.strftime("%d")

            # Source path (from smaller interval)
            source_dir = (
                config.IMAGE_OUTPUT_PATH
                / camera.safe_name
                / f"{source_interval}s"
                / year
                / month
                / day
            )
            source_file = source_dir / f"{camera.safe_name}_{timestamp}.jpg"

            # Destination path (for current interval)
            dest_dir = (
                config.IMAGE_OUTPUT_PATH
                / camera.safe_name
                / f"{interval}s"
                / year
                / month
                / day
            )
            dest_file = dest_dir / f"{camera.safe_name}_{timestamp}.jpg"

            # Check if source file exists and destination doesn't
            if source_file.exists() and not dest_file.exists():
                try:
                    # Create destination directory
                    dest_dir.mkdir(parents=True, exist_ok=True)

                    # Copy the file
                    shutil.copy2(source_file, dest_file)
                    reused_count += 1

                    logging.debug(
                        f"Reused {camera.safe_name} from {source_interval}s → {interval}s"
                    )

                except Exception as e:
                    logging.error(f"Failed to copy image for {camera.safe_name}: {e}")
            elif not source_file.exists():
                logging.debug(
                    f"Source file not found for {camera.safe_name}: {source_file}"
                )
                # Let's also check if the file was recently created
                parent_dir = source_file.parent
                if parent_dir.exists():
                    recent_files = [
                        f
                        for f in parent_dir.glob(f"{camera.safe_name}_*.jpg")
                        if abs(f.stat().st_mtime - timestamp) < 30
                    ]
                    if recent_files:
                        logging.debug(
                            f"Found {len(recent_files)} recent files for {camera.safe_name} but not exact timestamp"
                        )
            elif dest_file.exists():
                logging.debug(
                    f"Destination already exists for {camera.safe_name}: {dest_file}"
                )
                reused_count += 1  # Count as reused since we already have it

        if reused_count > 0:
            logging.info(
                f"{interval}s: Successfully reused {reused_count} images from {source_interval}s interval"
            )
        else:
            logging.warning(
                f"{interval}s: Failed to reuse any images from {source_interval}s interval"
            )

        return reused_count

    async def _run_summary(self):
        """Run periodic summary logging."""
        while self.running:
            await asyncio.sleep(config.SUMMARY_INTERVAL_SECONDS)

            if not self.running:
                break

            self._log_summary()

    def _update_stats(
        self, interval: int, results: Dict[str, bool], capture_time: datetime
    ):
        """Update statistics for an interval."""
        interval_stats = self.stats[interval]

        # Update overall stats
        interval_stats["last_capture_time"] = capture_time
        interval_stats["total_captures"] += len(results)

        # Update per-camera stats
        for camera_name, success in results.items():
            if success:
                interval_stats["successful_captures"] += 1
                interval_stats["camera_stats"][camera_name]["success"] += 1
            else:
                interval_stats["failed_captures"] += 1
                interval_stats["camera_stats"][camera_name]["failure"] += 1

    def _update_reuse_stats(
        self, interval: int, reused_count: int, capture_time: datetime
    ):
        """Update statistics when images are reused."""
        interval_stats = self.stats[interval]

        # Update overall stats
        interval_stats["last_capture_time"] = capture_time
        interval_stats["total_captures"] += reused_count
        interval_stats["successful_captures"] += reused_count
        interval_stats["reused_captures"] += reused_count

    def _log_summary(self):
        """Log periodic summary of statistics."""
        now = datetime.now()
        time_period = (now - self.last_summary_time).total_seconds()

        summary_lines = []
        summary_lines.append(f"Fetch Summary (last {time_period/60:.1f} minutes):")

        for interval in config.FETCH_INTERVALS:
            stats = self.stats[interval]

            if stats["total_captures"] == 0:
                summary_lines.append(f"  {interval}s: No captures")
                continue

            success_rate = (
                stats["successful_captures"] / stats["total_captures"]
            ) * 100
            last_capture = stats["last_capture_time"]
            last_capture_str = (
                last_capture.strftime("%H:%M:%S") if last_capture else "Never"
            )

            # Include reuse information in summary
            if stats["reused_captures"] > 0:
                summary_lines.append(
                    f"  {interval}s: {stats['successful_captures']}/{stats['total_captures']} "
                    f"successful ({success_rate:.1f}%), {stats['reused_captures']} reused, last: {last_capture_str}"
                )
            else:
                summary_lines.append(
                    f"  {interval}s: {stats['successful_captures']}/{stats['total_captures']} "
                    f"successful ({success_rate:.1f}%), last: {last_capture_str}"
                )

            # Camera-specific stats
            for camera_name, camera_stats in stats["camera_stats"].items():
                total = camera_stats["success"] + camera_stats["failure"]
                if total > 0:
                    cam_success_rate = (camera_stats["success"] / total) * 100
                    summary_lines.append(
                        f"    {camera_name}: {camera_stats['success']}/{total} ({cam_success_rate:.1f}%)"
                    )

        # Log all summary lines
        for line in summary_lines:
            logging.info(line)

        # Reset stats for next period
        self._reset_stats()
        self.last_summary_time = now

    def _reset_stats(self):
        """Reset statistics for the next summary period."""
        for interval in config.FETCH_INTERVALS:
            self.stats[interval].update(
                {
                    "total_captures": 0,
                    "successful_captures": 0,
                    "failed_captures": 0,
                    "reused_captures": 0,
                    "camera_stats": defaultdict(
                        lambda: {"success": 0, "failure": 0, "reused": 0}
                    ),
                }
            )

    def get_current_stats(self) -> Dict:
        """Get current statistics."""
        return dict(self.stats)
