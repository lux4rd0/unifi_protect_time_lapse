# app/fetch_service.py

import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List
import time

import config
from camera_manager import CameraManager


class FetchService:
    """Service for periodically fetching camera snapshots."""

    def __init__(self):
        self.camera_manager: CameraManager
        self.interval_tasks: List[asyncio.Task] = []
        self.running = False

        # Calculate common aligned timestamp ONCE for ALL intervals
        self.common_start_timestamp = config.find_common_aligned_timestamp()
        logging.info(
            f"FetchService initialized with common start timestamp: {self.common_start_timestamp}"
        )

        # Statistics tracking
        self.stats = {
            interval: {
                "total_captures": 0,
                "successful_captures": 0,
                "failed_captures": 0,
                "last_capture_time": None,
                "camera_stats": defaultdict(lambda: {"success": 0, "failure": 0}),
            }
            for interval in config.FETCH_INTERVALS
        }

        self.last_summary_time = datetime.now()

        logging.info(
            f"Fetch service initialized with intervals: {config.FETCH_INTERVALS}"
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
            cameras = await self.camera_manager.get_cameras(force_refresh=True)

            # Log camera distribution strategy
            use_distribution = config.should_use_camera_distribution(len(cameras))
            if use_distribution:
                optimal_offset = config.calculate_optimal_offset_seconds(len(cameras))
                logging.info(
                    f"Camera distribution ENABLED: {len(cameras)} cameras, "
                    f"strategy: {config.FETCH_DISTRIBUTION_STRATEGY}, "
                    f"offset: {optimal_offset}s"
                )
            else:
                logging.info(f"Camera distribution DISABLED: {len(cameras)} cameras")

            # Start interval tasks
            for interval in config.FETCH_INTERVALS:
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

        # ALL intervals use the exact same start timestamp
        next_execution = datetime.fromtimestamp(self.common_start_timestamp)

        # Log alignment status
        if self.common_start_timestamp % interval == 0:
            logging.info(
                f"{interval}s: Starting aligned with timestamp {self.common_start_timestamp}"
            )
        else:
            offset = self.common_start_timestamp % interval
            logging.info(
                f"{interval}s: Starting with {offset}s offset from natural alignment"
            )
            logging.info(
                f"{interval}s: Will execute every {interval}s from common start time"
            )

        # Wait for first execution
        sleep_time = (next_execution - datetime.now()).total_seconds()
        if sleep_time > 0:
            logging.info(
                f"{interval}s: First capture in {sleep_time:.1f}s at {next_execution.strftime('%H:%M:%S')}"
            )
            await asyncio.sleep(sleep_time)

        while self.running:
            capture_time = datetime.now()
            timestamp = int(capture_time.timestamp())

            # Check if it's time for this interval to capture (relative to common start time)
            elapsed_since_start = timestamp - self.common_start_timestamp
            if elapsed_since_start % interval != 0:
                # Not time for this interval - sleep until next second and check again
                await asyncio.sleep(1)
                continue

            try:
                # Determine capture method based on camera distribution setting
                cameras = await self.camera_manager.get_cameras()
                use_distribution = config.should_use_camera_distribution(len(cameras))

                if use_distribution:
                    results = await self.camera_manager.capture_cameras_distributed(
                        timestamp, interval
                    )
                    distribution_note = " (distributed)"
                else:
                    results = await self.camera_manager.capture_all_cameras(
                        timestamp, interval
                    )
                    distribution_note = ""

                # Update statistics
                self._update_stats(interval, results, capture_time)

                # Log interval summary
                successful = sum(1 for success in results.values() if success)
                total = len(results)
                logging.debug(
                    f"{interval}s: Captured {successful}/{total} at {capture_time.strftime('%H:%M:%S')}{distribution_note}"
                )

            except Exception as e:
                logging.error(f"Error in {interval}s interval capture: {e}")
                self.stats[interval]["failed_captures"] += 1

            # Calculate next execution time (maintain perfect timing from start)
            next_elapsed = ((elapsed_since_start // interval) + 1) * interval
            next_timestamp = self.common_start_timestamp + next_elapsed
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
                    "camera_stats": defaultdict(lambda: {"success": 0, "failure": 0}),
                }
            )

    def get_current_stats(self) -> Dict:
        """Get current statistics."""
        return dict(self.stats)
