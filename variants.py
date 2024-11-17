# variants.py
from pathlib import Path
import asyncio
from distraction import create_distraction_video
from utils import get_video_duration
import logging
import time


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Variants:
    def __init__(
        self,
        main_video: Path,
        distraction_folder: Path,
        result_folder: Path,
        low_quality: bool,
        overwrite_files: bool,
        hwaccel: str = 'none',
        semaphore: asyncio.Semaphore = None
    ):
        """
        Initializes the Variants class.

        :param main_video: Path to the main video.
        :param distraction_folder: Path to the folder containing distraction videos.
        :param result_folder: Path to the folder to save the result videos.
        :param low_quality: Flag to use low quality settings.
        :param overwrite_files: Flag to overwrite existing files.
        :param hwaccel: Hardware acceleration method ('none' or 'qsv').
        :param semaphore: Semaphore to limit the number of concurrent FFmpeg processes.
        """
        self.main_video = main_video
        self.distraction_folder = distraction_folder
        self.result_folder = result_folder
        self.low_quality = low_quality
        self.overwrite_files = overwrite_files
        self.hwaccel = hwaccel.lower()
        self.semaphore = semaphore or asyncio.Semaphore(4)  # Default: Max 4 concurrent processes

    def get_hwaccel_options(self):
        """
        Returns hardware acceleration and codec options based on the selected method.

        :return: Dictionary with encoding parameters.
        """
        if self.hwaccel == 'qsv':
            return {
                'codec': 'h264_qsv',  # Or 'hevc_qsv' for H.265
                'preset': 'fast',      # Encoding speed preset
                'bitrate': '5M'        # Video bitrate
            }
        else:
            return {
                'codec': 'libx264',   # Default software codec
                'preset': 'fast',
                'bitrate': '5M'
            }

    async def run_ffmpeg_command(self, command: list, variant_name: str):
        """
        Runs an FFmpeg command asynchronously and handles its execution.

        :param command: List of FFmpeg command arguments.
        :param variant_name: Name of the variant for logging.
        """
        async with self.semaphore:
            logger.info(f"Starting {variant_name}: {' '.join(command)}")
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await process.communicate()
            except Exception as e:
                logger.error(f"Error during {variant_name} execution: {e}")
                process.kill()
                await process.wait()
                raise

            if process.returncode != 0:
                logger.error(f"FFmpeg error in {variant_name}: {stderr.decode()}")
                raise Exception(f"FFmpeg process for {variant_name} ended with an error.")
            else:
                logger.info(f"{variant_name} completed successfully.")

    async def delete_file_with_retry(self, file_path: Path, retries: int = 3, delay: float = 1.0):
        """
        Attempts to delete a file with retries in case of permission errors.

        :param file_path: Path to the file to delete.
        :param retries: Number of retry attempts.
        :param delay: Delay between retries in seconds.
        """
        for attempt in range(retries):
            try:
                file_path.unlink(missing_ok=True)
                logger.info(f"Deleted temporary file: {file_path}")
                return
            except PermissionError as e:
                logger.warning(f"Failed to delete {file_path} (Attempt {attempt + 1}/{retries}): {e}")
                await asyncio.sleep(delay)
        logger.error(f"Could not delete temporary file after {retries} attempts: {file_path}")

    async def variant1(self):
        """
        Variant 1: Main video occupies the full screen with two distraction videos in opposite corners
        (top-left and bottom-right).
        """
        variant_name = "Variant1"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video1, used_videos1 = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
            distraction_video2, _ = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files,
                exclude_list=used_videos1
            )
        except Exception as e:
            logger.error(f"Error creating distraction videos for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant1.mp4'

        filter_complex = (
            '[1:v]scale=240:-2[dist1];'
            '[2:v]scale=240:-2[dist2];'
            '[0:v][dist1]overlay=10:10[tmp1];'
            '[tmp1][dist2]overlay=main_w-overlay_w-10:main_h-overlay_h-10,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',  # Logging level
            '-i', str(self.main_video),
            '-i', str(distraction_video1),
            '-i', str(distraction_video2),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',  # Set pixel format
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video1))
            await self.delete_file_with_retry(Path(distraction_video2))

    async def variant2(self):
        """
        Variant 2: Main video on the left, distraction video on the right, plus a small floating video in the top-left corner.
        """
        variant_name = "Variant2"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video1, used_videos1 = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
            distraction_video2, _ = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files,
                exclude_list=used_videos1
            )
        except Exception as e:
            logger.error(f"Error creating distraction videos for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant2.mp4'

        # Set fixed sizes for the main videos
        target_width = 540
        target_height = 960

        filter_complex = (
            f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
            f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
            '[main][dist]hstack=inputs=2[tmp];'
            '[2:v]scale=135:-2[overlay];'
            '[tmp][overlay]overlay=10:10,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video1),
            '-i', str(distraction_video2),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video1))
            await self.delete_file_with_retry(Path(distraction_video2))

    async def variant3(self):
        """
        Variant 3: Distraction video is overlaid in the top-left corner.
        """
        variant_name = "Variant3"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video, used_videos = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
        except Exception as e:
            logger.error(f"Error creating distraction video for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant3.mp4'

        filter_complex = (
            '[1:v]scale=270:-2[overlay];'
            '[0:v][overlay]overlay=10:10,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video))

    async def variant4(self):
        """
        Variant 4: Main video on the left, distraction video on the right. No floating video.
        """
        variant_name = "Variant4"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video, used_videos = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
        except Exception as e:
            logger.error(f"Error creating distraction video for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant4.mp4'

        # Set fixed sizes for the main videos
        target_width = 540
        target_height = 960

        filter_complex = (
            f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
            f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
            '[main][dist]hstack=inputs=2,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video))

    async def variant5(self):
        """
        Variant 5: Mirror version of Variant1.
        Distraction videos are placed in the top-right and bottom-left corners.
        """
        variant_name = "Variant5"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video1, used_videos1 = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
            distraction_video2, _ = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files,
                exclude_list=used_videos1
            )
        except Exception as e:
            logger.error(f"Error creating distraction videos for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant5.mp4'

        filter_complex = (
            '[1:v]scale=240:-2[dist1];'
            '[2:v]scale=240:-2[dist2];'
            '[0:v][dist1]overlay=main_w-overlay_w-10:10[tmp1];'
            '[tmp1][dist2]overlay=10:main_h-overlay_h-10,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video1),
            '-i', str(distraction_video2),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video1))
            await self.delete_file_with_retry(Path(distraction_video2))

    async def variant6(self):
        """
        Variant 6: Mirror version of Variant2.
        Main video on the right, distraction video on the left, plus a small floating video in the top-right corner.
        """
        variant_name = "Variant6"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video1, used_videos1 = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
            distraction_video2, _ = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files,
                exclude_list=used_videos1
            )
        except Exception as e:
            logger.error(f"Error creating distraction videos for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant6.mp4'

        # Set fixed sizes
        target_width = 540
        target_height = 960

        filter_complex = (
            f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
            f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
            '[dist][main]hstack=inputs=2[tmp];'
            '[2:v]scale=135:-2[overlay];'
            '[tmp][overlay]overlay=main_w-overlay_w-10:10,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video1),
            '-i', str(distraction_video2),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video1))
            await self.delete_file_with_retry(Path(distraction_video2))

    async def variant7(self):
        """
        Variant 7: Mirror version of Variant3.
        Distraction video is overlaid in the top-right corner.
        """
        variant_name = "Variant7"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video, used_videos = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
        except Exception as e:
            logger.error(f"Error creating distraction video for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant7.mp4'

        filter_complex = (
            '[1:v]scale=270:-2[overlay];'
            '[0:v][overlay]overlay=main_w-overlay_w-10:10,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video))

    async def variant8(self):
        """
        Variant 8: Mirror version of Variant4.
        Main video on the right, distraction video on the left. No floating video.
        """
        variant_name = "Variant8"
        main_duration = get_video_duration(self.main_video)

        try:
            distraction_video, used_videos = await create_distraction_video(
                duration=main_duration,
                distraction_folder=self.distraction_folder,
                low_quality=self.low_quality,
                overwrite_files=self.overwrite_files
            )
        except Exception as e:
            logger.error(f"Error creating distraction video for {variant_name}: {e}")
            return

        output_video = self.result_folder / 'variant8.mp4'

        # Set fixed sizes for the main videos
        target_width = 540
        target_height = 960

        filter_complex = (
            f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
            f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
            f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
            '[dist][main]hstack=inputs=2,fps=30,format=nv12[out]'
        )

        hw_options = self.get_hwaccel_options()

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', str(self.main_video),
            '-i', str(distraction_video),
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-map', '0:a?',
            '-c:v', hw_options['codec'],
            '-preset', hw_options['preset'],
            '-b:v', hw_options['bitrate'],
            '-pix_fmt', 'nv12',
            '-shortest',
            '-y' if self.overwrite_files else '-n',
            str(output_video)
        ]

        try:
            await self.run_ffmpeg_command(command, variant_name)
        except Exception as e:
            logger.error(f"{variant_name} ended with an error: {e}")
        finally:
            # Clean up temporary files with retries
            await self.delete_file_with_retry(Path(distraction_video))
