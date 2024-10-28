import logging
import os
import subprocess
import yt_dlp
import time
from typing import List

class AudioExtractor:
    SUPPORTED_FORMATS = ['mp3', 'wav', 'aac', 'm4a', 'flac']
    SUPPORTED_BITRATES = ['64k', '128k', '192k', '256k', '320k']

    def __init__(self, output_dir):
        # Use the exact path provided without any additional nesting
        self.output_dir = output_dir
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_audio(self, input_path, format='mp3', bitrate='192k', progress_callback=None, **kwargs):
        if format not in self.SUPPORTED_FORMATS:
            self.logger.error(f"Unsupported format. Supported formats: {self.SUPPORTED_FORMATS}")
            return False

        if bitrate not in self.SUPPORTED_BITRATES:
            self.logger.error(f"Unsupported bitrate. Supported bitrates: {self.SUPPORTED_BITRATES}")
            return False

        try:
            if input_path.startswith(('http://', 'https://', 'www.')):
                return self._extract_audio_from_youtube(input_path, format, bitrate, progress_callback, **kwargs)
            else:
                return self._extract_audio_from_file(input_path, format, bitrate, progress_callback, **kwargs)
        except Exception as e:
            self.logger.error(f"Error extracting audio: {str(e)}")
            return False

    def _extract_audio_from_youtube(self, url, format, bitrate, progress_callback, **kwargs):
        def yt_progress_hook(d):
            if d['status'] == 'downloading' and progress_callback:
                progress_callback(d['downloaded_bytes'] / d['total_bytes'])

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format,
                'preferredquality': bitrate,
            }],
            'outtmpl': os.path.join(self.output_dir, '%(title)s.%(ext)s'),
            'quiet': kwargs.get('quiet', True),
            'no_warnings': kwargs.get('no_warnings', True),
            'progress_hooks': [yt_progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self._update_file_modification_time(self.output_dir)
            self.logger.info(f"Audio extracted from YouTube: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Error extracting audio from YouTube {url}: {str(e)}")
            return False

    def _extract_audio_from_file(self, video_path, format, bitrate, progress_callback, **kwargs):
        try:
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            audio_output = os.path.join(self.output_dir, f"{video_name}.{format}")
            
            self.logger.info(f"Extracting audio from: {video_path}")
            self.logger.info(f"Output to: {audio_output}")

            # Enhanced FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-vn',  # Disable video
                '-acodec', 'libmp3lame' if format == 'mp3' else format,
                '-b:a', bitrate,
                '-ar', '44100',  # Standard sample rate
                '-ac', '2',      # Stereo
                '-threads', '0', # Use all available threads
                audio_output
            ]

            self.logger.info(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg with full output capture
            process = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero return code
            )

            # Check for errors
            if process.returncode != 0:
                self.logger.error(f"FFmpeg stderr: {process.stderr}")
                self.logger.error(f"FFmpeg stdout: {process.stdout}")
                raise Exception(f"FFmpeg failed with return code {process.returncode}")

            # Verify output file
            if not os.path.exists(audio_output):
                raise Exception(f"Audio output file was not created: {audio_output}")
            
            if os.path.getsize(audio_output) == 0:
                raise Exception(f"Audio output file is empty: {audio_output}")

            self.logger.info(f"Successfully extracted audio to: {audio_output}")
            return True

        except Exception as e:
            self.logger.error(f"Error extracting audio from file {video_path}: {str(e)}")
            # Add more detailed error information
            if 'process' in locals():
                self.logger.error(f"FFmpeg command output: {process.stdout}")
                self.logger.error(f"FFmpeg command error: {process.stderr}")
            return False

    def merge_audio_chunks(self, chunk_paths: List[str], output_path: str, format: str, bitrate: str):
        """Merge multiple audio files into one"""
        try:
            self.logger.info(f"Starting audio merge process for {len(chunk_paths)} chunks")
            self.logger.info(f"Output path: {output_path}")
            
            # Create a text file listing all audio chunks
            list_file = os.path.join(self.output_dir, 'chunks_list.txt')
            
            # Write audio chunk paths to list file
            with open(list_file, 'w', encoding='utf-8') as f:
                for audio_chunk in chunk_paths:
                    f.write(f"file '{audio_chunk}'\n")

            self.logger.info(f"Created chunks list file with {len(chunk_paths)} entries")

            # Merge audio chunks
            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c:a', format if format != 'mp3' else 'libmp3lame',
                '-b:a', bitrate,
                '-hide_banner',
                output_path
            ]
            
            self.logger.info(f"Running merge command: {' '.join(ffmpeg_cmd)}")
            
            # Run FFmpeg with proper error handling
            process = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                cwd=self.output_dir
            )
            
            if process.returncode != 0:
                self.logger.error(f"FFmpeg merge stderr: {process.stderr}")
                raise Exception(f"FFmpeg merge failed with return code {process.returncode}")

            # Verify the output file
            if not os.path.exists(output_path):
                raise Exception(f"Merged audio file was not created: {output_path}")
            
            if os.path.getsize(output_path) == 0:
                raise Exception(f"Merged audio file is empty: {output_path}")

            self.logger.info(f"Successfully created merged audio file: {output_path}")

            # Cleanup
            try:
                if os.path.exists(list_file):
                    os.remove(list_file)
                    self.logger.info("Removed chunks list file")
                
                for audio_chunk in chunk_paths:
                    if os.path.exists(audio_chunk):
                        os.remove(audio_chunk)
                        self.logger.info(f"Removed audio chunk: {audio_chunk}")
            except Exception as cleanup_error:
                self.logger.warning(f"Error during cleanup: {cleanup_error}")

            return True

        except Exception as e:
            self.logger.error(f"Error in merge_audio_chunks: {str(e)}")
            # Cleanup on error
            try:
                if 'list_file' in locals() and os.path.exists(list_file):
                    os.remove(list_file)
                for chunk in chunk_paths:
                    if os.path.exists(chunk):
                        os.remove(chunk)
            except Exception as cleanup_error:
                self.logger.warning(f"Error during error cleanup: {cleanup_error}")
            return False

    def _update_file_modification_time(self, path):
        current_time = time.time()
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    os.utime(file_path, (current_time, current_time))
        else:
            os.utime(path, (current_time, current_time))

    def _parse_duration(self, line):
        time_str = line.split("Duration: ")[1].split(",")[0]
        h, m, s = time_str.split(':')
        return float(h) * 3600 + float(m) * 60 + float(s)

    def _parse_time(self, line):
        time_str = line.split("time=")[1].split()[0]
        h, m, s = time_str.split(':')
        return float(h) * 3600 + float(m) * 60 + float(s)

