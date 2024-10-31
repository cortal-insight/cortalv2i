import cv2
import concurrent.futures
import os
from typing import Callable, Optional
import numpy as np

class VideoProcessor:
    def __init__(self, frames_dir: Optional[str] = None,
                 audio_dir: Optional[str] = None,
                 max_workers: int = 4):
        self.frames_dir = frames_dir
        self.audio_dir = audio_dir
        self.max_workers = max_workers

    def extract_frames(self, video_path: str, start_frame: int, end_frame: int, config: dict, progress_callback: Callable = None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        total_frames = end_frame - start_frame
        fps = cap.get(cv2.CAP_PROP_FPS)

        frame_count = 0
        method = config.get('method', 'fps')

        # Calculate frame interval based on method
        if method == 'fps':
            target_fps = config['params'].get('fps', 1.0)
            frame_interval = int(fps / target_fps)
        elif method == 'interval':
            interval = config['params'].get('interval', 1.0)
            frame_interval = int(interval * fps)
        elif method == 'scene':  # treat scene method as interval with 1 second
            frame_interval = int(fps)
        else:
            frame_interval = int(fps)  # default to 1 second interval

        # Get resolution if specified
        if 'resolution' in config:
            try:
                width, height = map(int, config['resolution'].split('*'))
            except:
                width, height = None, None
        else:
            width, height = None, None

        current_frame = start_frame
        frames_to_process = []

        while current_frame < end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            if (current_frame - start_frame) % frame_interval == 0:
                # Resize if resolution is specified
                if width and height:
                    frame = cv2.resize(frame, (width, height))

                output_path = os.path.join(
                    self.frames_dir,
                    f"frame_{current_frame:06d}.{config.get('output_format', 'jpg')}"
                )

                frames_to_process.append((frame.copy(), output_path))
                frame_count += 1

            current_frame += 1
            if progress_callback:
                progress = (current_frame - start_frame) / total_frames
                progress_callback(progress)

        # Process frames using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for frame, output_path in frames_to_process:
                futures.append(
                    executor.submit(
                        self._save_frame,
                        frame,
                        output_path,
                        config.get('output_format', 'jpg')
                    )
                )

            # Wait for all frames to be saved
            concurrent.futures.wait(futures)

        cap.release()

    def _save_frame(self, frame, output_path: str, format: str):
        """Save a single frame to disk"""
        try:
            if format.lower() == 'png':
                cv2.imwrite(output_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            else:
                cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        except Exception as e:
            print(f"Error saving frame to {output_path}: {str(e)}")

    def extract_audio(self, video_path: str, config: dict, progress_callback: Callable = None):
        """Extract audio from video"""
        try:
            import ffmpeg

            output_format = config.get('format', 'mp3')
            bitrate = config.get('bitrate', '192k')
            output_filename = os.path.splitext(os.path.basename(video_path))[0] + f".{output_format}"
            output_path = os.path.join(self.audio_dir, output_filename)

            # Extract audio using ffmpeg
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, output_path, acodec=output_format, audio_bitrate=bitrate)

            # Run the ffmpeg command
            ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)

            if progress_callback:
                progress_callback(1.0)  # Audio extraction completed

            return True
        except Exception as e:
            print(f"Error extracting audio: {str(e)}")
            return False

    def process_input(self, input_source: str, start_frame: int, end_frame: int, 
                      extraction_config: dict = None, audio_config: dict = None, 
                      progress_callback: Callable = None):
        """Process input source with given configurations"""
        if extraction_config and self.frames_dir:
            self.extract_frames(input_source, start_frame, end_frame, extraction_config, progress_callback)
        
        if audio_config and self.audio_dir:
            self.extract_audio(input_source, audio_config, progress_callback)