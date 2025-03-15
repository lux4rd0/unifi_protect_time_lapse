# app/create_time_lapse.py

import os
import subprocess
import argparse
import datetime
import logging
import shutil
from pathlib import Path

import glob
import time
import asyncio

import config


class CreateTimeLapse:
    def __init__(self):
        logging.basicConfig(
            level=config.UNIFI_TIME_LAPSE_LOGGING_LEVEL,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.semaphore = asyncio.Semaphore(
            config.UNIFI_TIME_LAPSE_FFMPEG_CONCURRENT_CREATION
        )  # Semaphore to ensure sequential execution

    async def format_file_size(self, size_in_bytes):  # Make it an asynchronous method
        """Formats the file size into a human-readable format."""
        if size_in_bytes < 1024:
            return f"{size_in_bytes} bytes"
        elif size_in_bytes < 1024**2:
            return f"{size_in_bytes / 1024:.2f} KB"
        elif size_in_bytes < 1024**3:
            return f"{size_in_bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{size_in_bytes / 1024 ** 3:.2f} GB"

    def format_duration(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

    async def create_time_lapse(self, days_ago, camera):
        # Extract camera name from the camera object
        camera_name = camera["name"] if isinstance(camera, dict) else camera

        async with self.semaphore:
            date = datetime.datetime.now() - datetime.timedelta(days=days_ago)
            date_year = date.strftime("%Y")
            date_month = date.strftime("%m")
            date_day = date.strftime("%d")

            frame_rate = config.UNIFI_TIME_LAPSE_FFMPEG_FRAME_RATE
            ffmpeg_loglevel = (
                "error" if logging.getLogger().level <= logging.INFO else "info"
            )

            for interval in config.UNIFI_TIME_LAPSE_FETCH_INTERVALS:
                interval_str = f"{interval}s"
                image_path = (
                    Path(config.UNIFI_TIME_LAPSE_IMAGE_OUTPUT_PATH)
                    / camera_name
                    / interval_str
                    / date_year
                    / date_month
                    / date_day
                )
                video_path = (
                    Path(config.UNIFI_TIME_LAPSE_VIDEO_OUTPUT_PATH)
                    / date_year
                    / date_month
                    / camera_name
                    / interval_str
                )

                try:
                    # Look only for PNG files
                    image_files = list(image_path.glob(f"{camera_name}_*.png"))

                    if not image_files:
                        logging.warning(
                            f"No PNG images found for {camera_name} in {image_path}. Skipping time-lapse creation."
                        )
                        continue  # Try next interval instead of returning
                except Exception as e:
                    logging.error(f"Error gathering image files: {e}")
                    continue  # Try next interval instead of returning

                logging.info(
                    f"Found {len(image_files)} PNG images for {camera_name} in {image_path}."
                )
                file_times = [file.stat().st_mtime for file in image_files]
                if not file_times:
                    logging.warning(
                        f"No valid files with timestamps for {camera_name}. Skipping."
                    )
                    continue

                earliest_file_time = min(file_times)
                latest_file_time = max(file_times)
                logging.info(
                    f"Earliest file timestamp for {camera_name}: {time.ctime(earliest_file_time)}"
                )
                logging.info(
                    f"Latest file timestamp for {camera_name}: {time.ctime(latest_file_time)}"
                )

                video_path.mkdir(parents=True, exist_ok=True)

                overwrite_flag = (
                    "-y" if config.UNIFI_TIME_LAPSE_FFMPEG_OVERWRITE_FILE else "-n"
                )
                output_file = (
                    video_path
                    / f"{camera_name}_{date_year}{date_month}{date_day}_{interval_str}.mp4"
                )

                # Use PNG-specific pattern
                input_pattern = str(image_path / f"{camera_name}_*.png")

                # Get active preset settings
                preset_config = config.UNIFI_TIME_LAPSE_ACTIVE_PRESET
                crf = preset_config["crf"]
                preset_speed = preset_config["preset"]
                pix_fmt = preset_config["pix_fmt"]
                use_color_settings = preset_config["color_settings"]

                # Base ffmpeg command
                ffmpeg_command = [
                    "ffmpeg",
                    overwrite_flag,
                    "-loglevel",
                    ffmpeg_loglevel,
                    "-nostats",
                    "-r",
                    str(frame_rate),
                    "-f",
                    "image2",
                    "-pattern_type",
                    "glob",
                    "-i",
                    input_pattern,
                    "-c:v",
                    "libx265",
                    "-x265-params",
                    f"log-level=0:crf={crf}",
                    "-preset",
                    preset_speed,
                    "-pix_fmt",
                    pix_fmt,
                ]

                # Add color settings if enabled in preset
                if use_color_settings:
                    ffmpeg_command.extend(
                        [
                            "-color_primaries",
                            "bt709",
                            "-color_trc",
                            "bt709",
                            "-colorspace",
                            "bt709",
                        ]
                    )

                # Add output file tag and path
                ffmpeg_command.extend(
                    [
                        "-tag:v",
                        "hvc1",
                        str(output_file),
                    ]
                )

                # Log the quality preset being used
                logging.info(
                    f"Using video quality preset: {config.UNIFI_TIME_LAPSE_VIDEO_QUALITY_PRESET} (CRF: {crf}, Preset: {preset_speed}, Format: {pix_fmt})"
                )

                start_time = time.time()
                logging.debug(f"Running FFmpeg command: {' '.join(ffmpeg_command)}")
                try:
                    process = await asyncio.create_subprocess_exec(
                        *ffmpeg_command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, stderr = await process.communicate()

                    end_time = time.time()
                    duration_seconds = end_time - start_time

                    if process.returncode != 0:
                        error_msg = (
                            stderr.decode("utf-8") if stderr else "Unknown error"
                        )
                        logging.error(
                            f"FFmpeg failed with return code {process.returncode}: {error_msg[:200]}..."
                        )
                        continue

                    if not output_file.exists() or output_file.stat().st_size == 0:
                        logging.error("The output file was not created or is empty.")
                        continue
                    else:
                        file_size = output_file.stat().st_size
                        formatted_size = await self.format_file_size(file_size)
                        human_readable_duration = self.format_duration(duration_seconds)

                        logging.info(
                            f"Successfully created time-lapse for {camera_name} in {human_readable_duration}. File size: {formatted_size}."
                        )

                        if config.UNIFI_TIME_LAPSE_FFMPEG_DELETE_IMAGES_AFTER_SUCCESS:
                            try:
                                shutil.rmtree(image_path)
                                logging.info(
                                    f"Deleted image files for {camera_name} at {image_path}."
                                )
                            except Exception as e:
                                logging.error(
                                    f"Failed to delete image files for {camera_name} at {image_path}. Error: {e}"
                                )
                        else:
                            logging.info(
                                f"No files deleted for {camera_name} based on configuration."
                            )
                except Exception as e:
                    logging.error(f"Error running ffmpeg for {camera_name}: {e}")

    async def create_time_lapse_for_days_ago(
        self, days_ago
    ):  # Make it an asynchronous method
        tasks = []
        for camera in config.UNIFI_TIME_LAPSE_CAMERAS:
            camera_name = camera["name"] if isinstance(camera, dict) else camera
            logging.info(f"Creating time-lapse for camera: {camera_name}")
            task = asyncio.create_task(
                self.create_time_lapse(days_ago, camera)
            )  # Create a task for each camera
            tasks.append(task)
        await asyncio.gather(*tasks)  # Run all tasks concurrently


def main():
    days_ago = config.UNIFI_TIME_LAPSE_DAYS_AGO
    time_lapse_creator = CreateTimeLapse()
    asyncio.run(
        time_lapse_creator.create_time_lapse_for_days_ago(days_ago)
    )  # Run the main asynchronous method with asyncio.run()


if __name__ == "__main__":
    main()
