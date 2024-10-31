import os
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class AudioExtractor:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def extract_audio(self, video_path: str, format: str = 'mp3', bitrate: str = '192k',
                      progress_callback=None, start_time: float = None, end_time: float = None,
                      chunk_index: int = None):
        """
        Extract audio from video file, optionally in chunks.

        Args:
            video_path: Path to input video file
            format: Output audio format (mp3, wav, etc.)
            bitrate: Audio bitrate
            progress_callback: Callback function for progress updates
            start_time: Start time in seconds for chunk extraction
            end_time: End time in seconds for chunk extraction
            chunk_index: Index of current chunk (for filename)
        """
        try:
            video_name = Path(video_path).stem
            if chunk_index is not None:
                output_filename = f"{video_name}_chunk{chunk_index}.{format}"
            else:
                output_filename = f"{video_name}.{format}"
            output_path = os.path.join(self.output_dir, output_filename)

            # Base ffmpeg command
            cmd = ['ffmpeg', '-y', '-i', video_path]

            # Add time parameters if chunking
            if start_time is not None and end_time is not None:
                duration = end_time - start_time
                cmd.extend(['-ss', str(start_time), '-t', str(duration)])

            # Add encoding parameters
            cmd.extend([
                '-vn',  # No video
                '-acodec', self._get_codec(format),
                '-ab', bitrate,
                '-ar', '44100',  # Sample rate
                '-ac', '2',  # Stereo
                output_path
            ])

            # Run ffmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # Monitor progress
            duration = end_time - start_time if (start_time is not None and end_time is not None) else self._get_duration(video_path)
            self._monitor_progress(process, duration, progress_callback)

            # Check if extraction was successful
            if process.returncode == 0:
                logger.info(f"Successfully extracted audio to: {output_path}")
                return True
            else:
                raise Exception(f"FFmpeg process failed with return code {process.returncode}")

        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            raise

    def _get_codec(self, format: str) -> str:
        """Map format to ffmpeg codec name."""
        codec_map = {
            'mp3': 'libmp3lame',
            'aac': 'aac',
            'm4a': 'aac',
            'wav': 'pcm_s16le',
            'flac': 'flac'
        }
        return codec_map.get(format, 'libmp3lame')

    def _get_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())

    def _monitor_progress(self, process, duration: float, progress_callback=None):
        """Monitor ffmpeg progress and call progress callback."""
        time_processed = 0
        last_progress = 0
        while True:
            line = process.stderr.readline()
            if not line:
                break
            # Parse ffmpeg output to find time
            if "time=" in line:
                try:
                    # Extract time in format HH:MM:SS.ms
                    time_str = line.split("time=")[1].split()[0]
                    # Handle different time formats
                    if '.' in time_str:
                        time_str = time_str.split('.')[0]  # Remove milliseconds
                    if ':' in time_str:
                        h, m, s = time_str.split(':')
                        time_processed = float(h) * 3600 + float(m) * 60 + float(s)
                    else:
                        time_processed = float(time_str)
                    if progress_callback and duration > 0:
                        progress = min(time_processed / duration, 1.0)
                        # Only update if progress has changed significantly (avoid too frequent updates)
                        if progress - last_progress >= 0.01:  # Update every 1%
                            progress_callback(progress)
                            last_progress = progress
                except Exception as e:
                    logger.debug(f"Error parsing progress: {str(e)}")
                    pass

        # Ensure we show 100% at the end
        if progress_callback and last_progress < 1.0:
            progress_callback(1.0)

        process.wait()