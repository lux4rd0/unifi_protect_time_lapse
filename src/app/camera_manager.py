# app/camera_manager.py

import httpx  # type: ignore
import asyncio
import logging
import hashlib
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

import config

# Disable SSL warnings if SSL verification is disabled
if not config.UNIFI_PROTECT_VERIFY_SSL:
    import urllib3  # type: ignore

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class Camera:
    """Data class representing a camera."""

    id: str
    name: str
    state: str
    type: str
    mac: str
    firmware_version: str
    is_connected: bool
    is_recording: bool
    supports_full_hd_snapshot: bool = False

    @classmethod
    def from_api_response(cls, camera_data: Dict[str, Any]) -> "Camera":
        """Create Camera instance from API response data."""
        # Extract feature flags
        feature_flags = camera_data.get("featureFlags", {})
        supports_full_hd = feature_flags.get("supportFullHdSnapshot", False)

        return cls(
            id=camera_data.get("id", ""),
            name=camera_data.get("name", ""),
            state=camera_data.get("state", ""),
            type=camera_data.get("type", ""),
            mac=camera_data.get("mac", ""),
            firmware_version=camera_data.get("firmwareVersion", ""),
            is_connected=camera_data.get("state") == "CONNECTED",
            is_recording=camera_data.get("isRecording", False),
            supports_full_hd_snapshot=supports_full_hd,
        )

    @property
    def safe_name(self) -> str:
        """Return a filesystem-safe version of the camera name."""
        return self.name.replace(" ", "_").replace("/", "_").replace("\\", "_")

    def get_deterministic_offset(self, offset_seconds: int) -> int:
        """
        Get consistent offset for this camera based on camera ID hash.

        Uses camera ID (immutable) instead of name (can be changed).
        This ensures the same camera always gets the same offset,
        even across container restarts and camera list changes.

        Args:
            offset_seconds: Seconds between offset slots

        Returns:
            Offset in seconds (0 to 59)
        """
        # Use camera ID for maximum stability - never changes
        hash_obj = hashlib.sha1(self.id.encode("utf-8"))
        hash_int = int(hash_obj.hexdigest(), 16)

        # Calculate number of possible offset slots based on config
        slots = config.FETCH_DISTRIBUTION_WINDOW_SECONDS // offset_seconds
        slot = hash_int % slots

        return slot * offset_seconds


class CameraManager:
    """Manages camera discovery and snapshot capture."""

    def __init__(self):
        self.client: httpx.AsyncClient
        self.cameras: List[Camera] = []
        self.last_camera_refresh = None
        self.camera_refresh_interval = config.CAMERA_REFRESH_INTERVAL

    async def __aenter__(self):
        """Async context manager entry."""
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        timeout = httpx.Timeout(config.UNIFI_PROTECT_REQUEST_TIMEOUT)

        self.client = httpx.AsyncClient(
            verify=config.UNIFI_PROTECT_VERIFY_SSL,
            limits=limits,
            timeout=timeout,
            headers={"User-Agent": "UniFi-Protect-Time-Lapse/2.0"},
        )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self, "client"):
            await self.client.aclose()

    async def refresh_cameras(self, force: bool = False) -> List[Camera]:
        """
        Refresh the list of cameras from the API.

        Args:
            force: Force refresh even if cache is still valid

        Returns:
            List of Camera objects
        """
        now = datetime.now()

        # Check if we need to refresh
        if (
            not force
            and self.last_camera_refresh
            and self.cameras
            and (now - self.last_camera_refresh).total_seconds()
            < self.camera_refresh_interval
        ):
            return self.cameras

        try:
            url = f"{config.UNIFI_PROTECT_BASE_URL}/cameras"

            response = await self.client.get(url, headers=config.get_json_headers())
            response.raise_for_status()
            cameras_data = response.json()

            # Convert API response to Camera objects
            all_cameras = [
                Camera.from_api_response(cam_data) for cam_data in cameras_data
            ]

            # Filter cameras based on configuration
            filtered_cameras = [
                camera
                for camera in all_cameras
                if config.should_process_camera(camera.name)
            ]

            self.cameras = filtered_cameras
            self.last_camera_refresh = now

            logging.info(
                f"Discovered {len(all_cameras)} total cameras, {len(filtered_cameras)} will be processed"
            )

            # Log all discovered camera names for debugging
            if all_cameras:
                camera_names = [f'"{camera.name}"' for camera in all_cameras]
                logging.info(f"Available cameras: {', '.join(camera_names)}")

            # Log camera details for cameras we'll process
            if filtered_cameras:
                for camera in filtered_cameras:
                    status = "✓" if camera.is_connected else "✗"
                    hd_support = "HD" if camera.supports_full_hd_snapshot else "SD"
                    logging.info(
                        f"  {status} {camera.name} ({camera.state}) - {camera.type} [{hd_support}]"
                    )

                # Log camera distribution information if enabled
                use_distribution = config.should_use_camera_distribution(
                    len(filtered_cameras)
                )
                if use_distribution:
                    optimal_offset = config.calculate_optimal_offset_seconds(
                        len(filtered_cameras)
                    )

                    logging.info(
                        f"Camera distribution ENABLED: {len(filtered_cameras)} cameras, "
                        f"strategy: {config.FETCH_DISTRIBUTION_STRATEGY}, "
                        f"offset: {optimal_offset}s"
                    )

                    # Log rate limit analysis
                    max_simultaneous_intervals = (
                        config.calculate_max_simultaneous_intervals()
                    )
                    effective_concurrent_limit = (
                        config.calculate_effective_concurrent_limit()
                    )

                    logging.info(
                        f"Rate limit analysis: "
                        f"limit={config.UNIFI_PROTECT_RATE_LIMIT} req/sec, "
                        f"effective={config.EFFECTIVE_RATE_LIMIT} req/sec, "
                        f"max_intervals={max_simultaneous_intervals}, "
                        f"concurrent_limit={effective_concurrent_limit}"
                    )

                    if config.FETCH_LOG_SLOT_UTILIZATION:
                        self._log_camera_assignments(filtered_cameras, optimal_offset)
                else:
                    logging.info(
                        f"Camera distribution DISABLED: {len(filtered_cameras)} cameras"
                    )

                    # Log why distribution is disabled
                    if config.FETCH_ENABLE_CAMERA_DISTRIBUTION == "false":
                        logging.info("  Reason: Explicitly disabled in configuration")
                    else:
                        # Check rate limit compliance without distribution
                        config.validate_rate_limit_compliance(len(filtered_cameras))

            else:
                logging.warning("No cameras match the current selection criteria")
                if config.CAMERA_SELECTION_MODE == "whitelist":
                    logging.warning(f"Whitelist: {config.CAMERA_WHITELIST}")
                elif config.CAMERA_SELECTION_MODE == "blacklist":
                    logging.warning(f"Blacklist: {config.CAMERA_BLACKLIST}")

            return self.cameras

        except httpx.RequestError as e:
            logging.error(f"Failed to fetch cameras: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error fetching cameras: {e}")
            raise

    def _log_camera_assignments(self, cameras: List[Camera], offset_seconds: int):
        """Log camera slot assignments for debugging."""
        connected_cameras = [cam for cam in cameras if cam.is_connected]

        if not connected_cameras:
            return

        # Group cameras by their assigned slots
        slot_assignments = defaultdict(list)
        for camera in connected_cameras:
            offset = camera.get_deterministic_offset(offset_seconds)
            slot = offset // offset_seconds
            slot_assignments[slot].append(camera.name)

        # Calculate max cameras per slot based on rate limits
        max_simultaneous_intervals = config.calculate_max_simultaneous_intervals()
        max_cameras_per_slot = config.EFFECTIVE_RATE_LIMIT // max_simultaneous_intervals

        logging.info("Camera slot assignments (deterministic):")
        for slot in sorted(slot_assignments.keys()):
            camera_names = slot_assignments[slot]
            offset = slot * offset_seconds
            logging.info(f"  Slot {slot} (+{offset}s): {', '.join(camera_names)}")

            # Warn if slot exceeds rate limit capacity
            if len(camera_names) > max_cameras_per_slot:
                logging.warning(
                    f"  ⚠️  Slot {slot} has {len(camera_names)} cameras "
                    f"(exceeds rate limit capacity of {max_cameras_per_slot})"
                )

    async def get_cameras(self, force_refresh: bool = False) -> List[Camera]:
        """
        Get the list of cameras, refreshing if necessary.

        Args:
            force_refresh: Force refresh from API

        Returns:
            List of Camera objects
        """
        if not self.cameras or force_refresh:
            await self.refresh_cameras(force=force_refresh)

        return self.cameras

    async def capture_snapshot(
        self, camera: Camera, output_path: str, interval: int, retry_count: int = 0
    ) -> bool:
        """
        Capture a snapshot from the specified camera.

        Args:
            camera: Camera object to capture from
            output_path: Path to save the image
            interval: Interval in seconds (for logging)
            retry_count: Current retry attempt (for internal use)

        Returns:
            True if successful, False otherwise
        """
        if not camera.is_connected:
            logging.debug(
                f"[{interval}s] Skipping {camera.name} - not connected (state: {camera.state})"
            )
            return False

        try:
            url = f"{config.UNIFI_PROTECT_BASE_URL}/cameras/{camera.id}/snapshot"

            # Build query parameters - only use highQuality if camera supports it
            params = {}
            if config.SNAPSHOT_HIGH_QUALITY and camera.supports_full_hd_snapshot:
                params["highQuality"] = "true"
                quality_note = "HQ"
            else:
                quality_note = "STD"

            # Log the request we're about to make
            logging.debug(f"[{interval}s] Requesting snapshot from {camera.name}")

            response = await self.client.get(
                url, headers=config.get_image_headers(), params=params
            )

            if response.status_code == 200:
                content_type = response.headers.get("Content-Type", "")

                if content_type.startswith("image/"):
                    # Ensure directory exists
                    import os

                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                    # Write image data
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    # Verify file was written and has reasonable size
                    if (
                        os.path.exists(output_path)
                        and os.path.getsize(output_path) > 1000
                    ):
                        file_size = os.path.getsize(output_path)
                        logging.debug(
                            f"[{interval}s] ✓ Captured {camera.name} [{quality_note}] -> {output_path} ({file_size/1024:.1f}KB)"
                        )
                        return True
                    else:
                        logging.error(
                            f"[{interval}s] ✗ Image file too small or missing: {camera.name}"
                        )
                        return False
                else:
                    logging.error(
                        f"[{interval}s] ✗ Invalid content type for {camera.name}: {content_type}"
                    )
                    return False
            else:
                # Try to get error details
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Unknown error")
                except:
                    error_msg = f"HTTP {response.status_code}"

                logging.error(
                    f"[{interval}s] ✗ Snapshot failed for {camera.name}: {error_msg}"
                )
                return False

        except httpx.TimeoutException:
            logging.error(f"[{interval}s] ✗ Timeout capturing {camera.name}")
            return False
        except httpx.RequestError as e:
            logging.error(f"[{interval}s] ✗ Network error capturing {camera.name}: {e}")
            return False
        except Exception as e:
            logging.error(
                f"[{interval}s] ✗ Unexpected error capturing {camera.name}: {e}"
            )
            return False

    async def capture_snapshot_with_retry(
        self, camera: Camera, output_path: str, interval: int
    ) -> bool:
        """
        Capture a snapshot with retry logic.

        Args:
            camera: Camera object to capture from
            output_path: Path to save the image
            interval: Interval in seconds (for logging)

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(config.FETCH_MAX_RETRIES + 1):
            success = await self.capture_snapshot(
                camera, output_path, interval, attempt
            )

            if success:
                return True

            if attempt < config.FETCH_MAX_RETRIES:
                logging.debug(
                    f"[{interval}s] Retrying {camera.name} in {config.FETCH_RETRY_DELAY}s (attempt {attempt + 1}/{config.FETCH_MAX_RETRIES})"
                )
                await asyncio.sleep(config.FETCH_RETRY_DELAY)

        logging.error(
            f"[{interval}s] Failed to capture {camera.name} after {config.FETCH_MAX_RETRIES + 1} attempts"
        )
        return False

    async def capture_all_cameras(
        self, timestamp: int, interval: int
    ) -> Dict[str, bool]:
        """
        Capture snapshots from all configured cameras concurrently.

        Args:
            timestamp: Unix timestamp for the capture
            interval: Interval in seconds (for directory structure)

        Returns:
            Dictionary mapping camera names to success status
        """
        cameras = await self.get_cameras()

        if not cameras:
            logging.warning("No cameras available for capture")
            return {}

        # Filter out disconnected cameras
        connected_cameras = [camera for camera in cameras if camera.is_connected]
        disconnected_cameras = [camera for camera in cameras if not camera.is_connected]

        # Log disconnected cameras
        if disconnected_cameras:
            disconnected_names = [cam.name for cam in disconnected_cameras]
            logging.warning(
                f"Skipping {len(disconnected_cameras)} disconnected cameras: {', '.join(disconnected_names)}"
            )

        if not connected_cameras:
            logging.warning("No connected cameras available for capture")
            return {}

        logging.debug(
            f"[{interval}s] Capturing from {len(connected_cameras)} connected cameras"
        )

        # Create semaphore to limit concurrent requests - use new config function
        concurrent_limit = config.calculate_effective_concurrent_limit()
        semaphore = asyncio.Semaphore(concurrent_limit)

        async def capture_with_semaphore(camera: Camera) -> tuple[str, bool]:
            async with semaphore:
                # Build output path
                date_obj = datetime.fromtimestamp(timestamp)
                year = date_obj.strftime("%Y")
                month = date_obj.strftime("%m")
                day = date_obj.strftime("%d")

                output_dir = (
                    config.IMAGE_OUTPUT_PATH
                    / camera.safe_name
                    / f"{interval}s"
                    / year
                    / month
                    / day
                )
                output_path = output_dir / f"{camera.safe_name}_{timestamp}.jpg"

                success = await self.capture_snapshot_with_retry(
                    camera, str(output_path), interval
                )
                return camera.name, success

        # Execute all captures concurrently (only connected cameras)
        tasks = [capture_with_semaphore(camera) for camera in connected_cameras]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        capture_results = {}
        for result in results:
            if isinstance(result, tuple):
                camera_name, success = result
                capture_results[camera_name] = success
            else:
                logging.error(f"Unexpected error in camera capture: {result}")

        # Log summary
        successful = sum(1 for success in capture_results.values() if success)
        total = len(capture_results)
        logging.info(f"[{interval}s] Captured {successful}/{total} connected cameras")

        return capture_results

    async def capture_cameras_distributed(
        self, timestamp: int, interval: int
    ) -> Dict[str, bool]:
        """
        Capture snapshots from cameras using distributed timing to avoid rate limits.

        Args:
            timestamp: Base unix timestamp for the capture
            interval: Interval in seconds (for directory structure)

        Returns:
            Dictionary mapping camera names to success status
        """
        cameras = await self.get_cameras()

        if not cameras:
            logging.warning("No cameras available for capture")
            return {}

        # Filter out disconnected cameras
        connected_cameras = [camera for camera in cameras if camera.is_connected]
        disconnected_cameras = [camera for camera in cameras if not camera.is_connected]

        # Log disconnected cameras
        if disconnected_cameras:
            disconnected_names = [cam.name for cam in disconnected_cameras]
            logging.warning(
                f"Skipping {len(disconnected_cameras)} disconnected cameras: {', '.join(disconnected_names)}"
            )

        if not connected_cameras:
            logging.warning("No connected cameras available for capture")
            return {}

        # Calculate optimal offset based on current camera count
        optimal_offset = config.calculate_optimal_offset_seconds(len(connected_cameras))

        # Group cameras by their offset
        camera_groups: Dict[int, List[Camera]] = defaultdict(list)
        for camera in connected_cameras:
            offset = camera.get_deterministic_offset(optimal_offset)
            camera_groups[offset].append(camera)

        logging.debug(
            f"[{interval}s] Capturing {len(connected_cameras)} cameras in {len(camera_groups)} groups "
            f"with {optimal_offset}s offsets (strategy: {config.FETCH_DISTRIBUTION_STRATEGY})"
        )

        # Execute captures for each group with proper timing
        all_results = {}

        for offset, group_cameras in sorted(camera_groups.items()):
            logging.debug(
                f"[{interval}s] Capturing group at +{offset}s: {[cam.name for cam in group_cameras]}"
            )

            # Create semaphore for this group - use new config function
            concurrent_limit = config.calculate_effective_concurrent_limit()
            semaphore = asyncio.Semaphore(min(len(group_cameras), concurrent_limit))

            async def capture_camera_in_group(camera: Camera) -> tuple[str, bool]:
                async with semaphore:
                    # Build output path using actual capture timestamp
                    actual_capture_timestamp = timestamp + offset
                    date_obj = datetime.fromtimestamp(actual_capture_timestamp)
                    year = date_obj.strftime("%Y")
                    month = date_obj.strftime("%m")
                    day = date_obj.strftime("%d")

                    output_dir = (
                        config.IMAGE_OUTPUT_PATH
                        / camera.safe_name
                        / f"{interval}s"
                        / year
                        / month
                        / day
                    )
                    # Use actual capture timestamp for accurate filenames
                    actual_capture_timestamp = timestamp + offset
                    output_path = (
                        output_dir
                        / f"{camera.safe_name}_{actual_capture_timestamp}.jpg"
                    )

                    success = await self.capture_snapshot_with_retry(
                        camera, str(output_path), interval
                    )
                    return camera.name, success

            # Execute captures for this group
            tasks = [capture_camera_in_group(camera) for camera in group_cameras]
            group_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process group results
            for result in group_results:
                if isinstance(result, tuple):
                    camera_name, success = result
                    all_results[camera_name] = success
                else:
                    logging.error(f"Unexpected error in camera capture: {result}")

            # Wait before next group (if there are more groups)
            remaining_groups = len([o for o in camera_groups.keys() if o > offset])
            if remaining_groups > 0:
                await asyncio.sleep(optimal_offset)

                # Log summary
        successful = sum(1 for success in all_results.values() if success)
        total = len(all_results)
        logging.info(
            f"[{interval}s] Captured {successful}/{total} connected cameras "
            f"(distributed across {len(camera_groups)} groups, {optimal_offset}s offset)"
        )

        return all_results
