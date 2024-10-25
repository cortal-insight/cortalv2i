import logging
import os
import subprocess
import yt_dlp
import time

class AudioExtractor:
    SUPPORTED_FORMATS = ['mp3', 'wav', 'aac', 'm4a', 'flac']
    SUPPORTED_BITRATES = ['64k', '128k', '192k', '256k', '320k']

    def __init__(self, output_dir):
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
            ffmpeg_cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # Disable video
                '-acodec', format,
                '-b:a', bitrate,
                '-ar', kwargs.get('sample_rate', '44100'),  # Sample rate
                '-ac', kwargs.get('channels', '2'),  # Number of channels
                audio_output
            ]

            process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            for line in process.stderr:
                if "Duration" in line:
                    duration = self._parse_duration(line)
                elif "time=" in line and duration and progress_callback:
                    current_time = self._parse_time(line)
                    progress = current_time / duration
                    progress_callback(progress)

            process.wait()
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {process.stderr.read()}")

            self._update_file_modification_time(audio_output)
            self.logger.info(f"Audio extracted: {audio_output}")
            return True
        except Exception as e:
            self.logger.error(f"Error extracting audio from file {video_path}: {str(e)}")
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