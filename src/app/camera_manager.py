# app/camera_manager.py

import httpx  # type: ignore
import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

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
        self, camera: Camera, output_path: str, retry_count: int = 0
    ) -> bool:
        """
        Capture a snapshot from the specified camera.

        Args:
            camera: Camera object to capture from
            output_path: Path to save the image
            retry_count: Current retry attempt (for internal use)

        Returns:
            True if successful, False otherwise
        """
        if not camera.is_connected:
            logging.debug(
                f"Skipping {camera.name} - not connected (state: {camera.state})"
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
                            f"✓ Captured {camera.name} [{quality_note}] -> {output_path} ({file_size/1024:.1f}KB)"
                        )
                        return True
                    else:
                        logging.error(
                            f"✗ Image file too small or missing: {camera.name}"
                        )
                        return False
                else:
                    logging.error(
                        f"✗ Invalid content type for {camera.name}: {content_type}"
                    )
                    return False
            else:
                # Try to get error details
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", "Unknown error")
                except:
                    error_msg = f"HTTP {response.status_code}"

                logging.error(f"✗ Snapshot failed for {camera.name}: {error_msg}")
                return False

        except httpx.TimeoutException:
            logging.error(f"✗ Timeout capturing {camera.name}")
            return False
        except httpx.RequestError as e:
            logging.error(f"✗ Network error capturing {camera.name}: {e}")
            return False
        except Exception as e:
            logging.error(f"✗ Unexpected error capturing {camera.name}: {e}")
            return False

    async def capture_snapshot_with_retry(
        self, camera: Camera, output_path: str
    ) -> bool:
        """
        Capture a snapshot with retry logic.

        Args:
            camera: Camera object to capture from
            output_path: Path to save the image

        Returns:
            True if successful, False otherwise
        """
        for attempt in range(config.FETCH_MAX_RETRIES + 1):
            success = await self.capture_snapshot(camera, output_path, attempt)

            if success:
                return True

            if attempt < config.FETCH_MAX_RETRIES:
                logging.debug(
                    f"Retrying {camera.name} in {config.FETCH_RETRY_DELAY}s (attempt {attempt + 1}/{config.FETCH_MAX_RETRIES})"
                )
                await asyncio.sleep(config.FETCH_RETRY_DELAY)

        logging.error(
            f"Failed to capture {camera.name} after {config.FETCH_MAX_RETRIES + 1} attempts"
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

        logging.debug(f"Capturing from {len(connected_cameras)} connected cameras")

        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(config.FETCH_CONCURRENT_LIMIT)

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
                    camera, str(output_path)
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
        logging.info(
            f"Captured {successful}/{total} connected cameras for {interval}s interval"
        )

        return capture_results
