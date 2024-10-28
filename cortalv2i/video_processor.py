import cv2
import os
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import yt_dlp
from typing import List, Union, Dict
import pandas as pd
from cortalv2i.frame_extractor import (
    FPSFrameExtractor,
    TimeIntervalFrameExtractor,
    ChangeDetectionFrameExtractor
)
from cortalv2i.audio_extractor import AudioExtractor

class VideoProcessor:
    def __init__(self, frames_dir: str, audio_dir: str = None, max_workers: int = None):
        self.frames_dir = frames_dir
        self.audio_dir = audio_dir
        self.max_workers = max_workers or os.cpu_count()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initialized VideoProcessor with frames_dir: {frames_dir}, audio_dir: {audio_dir}")

    def _get_frame_extractor(self, extraction_config: Dict):
        """
        Create and return appropriate frame extractor based on configuration
        """
        try:
            method = extraction_config.get('method')
            params = extraction_config.get('params', {})
            output_format = extraction_config.get('output_format', 'jpg')
            resolution = extraction_config.get('resolution', None)

            if method == "1" and params.get('fps'):
                return FPSFrameExtractor(
                    self.frames_dir,
                    fps=params['fps'],
                    output_format=output_format,
                    resolution=resolution
                )
            elif method == "2" and params.get('time_interval'):
                return TimeIntervalFrameExtractor(
                    self.frames_dir,
                    time_interval=params['time_interval'],
                    output_format=output_format,
                    resolution=resolution
                )
            elif method == "3" and params.get('threshold'):
                return ChangeDetectionFrameExtractor(
                    self.frames_dir,
                    threshold=params['threshold'],
                    output_format=output_format,
                    resolution=resolution
                )
            else:
                self.logger.error("Invalid extraction configuration")
                return None
        except Exception as e:
            self.logger.error(f"Error creating frame extractor: {str(e)}")
            return None

    def process_input(self, input_source: Union[str, List[str]],
                      extraction_config: Dict,
                      audio_config: Dict = None,
                      progress_callback=None):
        """
        Process various input sources including files, directories, and URLs
        """
        try:
            self.logger.info(f"Processing input source: {input_source}")
            self.logger.info(f"Audio config: {audio_config}")
            
            if isinstance(input_source, str):
                if os.path.isfile(input_source):
                    if input_source.endswith(('.txt', '.csv')):
                        self._process_list_file(input_source, extraction_config, audio_config, progress_callback)
                    else:
                        self._process_video_file(input_source, extraction_config, audio_config, progress_callback)
                elif os.path.isdir(input_source):
                    self._process_directory(input_source, extraction_config, audio_config, progress_callback)
                elif input_source.startswith(('http://', 'https://', 'www.')):
                    self._process_url(input_source, extraction_config, audio_config, progress_callback)
            elif isinstance(input_source, list):
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [
                        executor.submit(self.process_input, src, extraction_config, audio_config, progress_callback)
                        for src in input_source
                    ]
                    for future in futures:
                        future.result()
        except Exception as e:
            self.logger.error(f"Error processing input source: {str(e)}")
            raise  # Add raise to propagate the error

    def _process_list_file(self, file_path: str, extraction_config: Dict, audio_config: Dict, progress_callback=None):
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
                urls = df['url'].tolist() if 'url' in df.columns else df.iloc[:, 0].tolist()
            else:
                with open(file_path, 'r') as f:
                    urls = [line.strip() for line in f if line.strip()]

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._process_url, url, extraction_config, audio_config, progress_callback)
                    for url in urls
                ]
                for future in futures:
                    future.result()
        except Exception as e:
            self.logger.error(f"Error processing list file {file_path}: {str(e)}")

    def _process_directory(self, dir_path: str, extraction_config: Dict, audio_config: Dict, progress_callback=None):
        try:
            video_files = [
                os.path.join(dir_path, f) for f in os.listdir(dir_path)
                if f.endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv'))
            ]
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self._process_video_file, video_path, extraction_config, audio_config, progress_callback)
                    for video_path in video_files
                ]
                for future in futures:
                    future.result()
        except Exception as e:
            self.logger.error(f"Error processing directory {dir_path}: {str(e)}")

    def _process_video_file(self, video_path: str, extraction_config: Dict, audio_config: Dict, progress_callback=None):
        try:
            self.logger.info(f"Processing video file: {video_path}")
            self.logger.info(f"Audio config: {audio_config}")
            self.logger.info(f"Audio directory: {self.audio_dir}")
            
            # Extract frames
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"Could not open video file: {video_path}")
            
            # Extract frames if extractor is configured
            extractor = self._get_frame_extractor(extraction_config)
            if extractor:
                # Create a simple progress callback if none provided
                if progress_callback is None:
                    progress_callback = lambda x: None
                    
                frames_extracted = extractor.extract_frames(cap, progress_callback)
                self.logger.info(f"Extracted {frames_extracted} frames from {video_path}")
            
            cap.release()

            # Extract audio if configured and audio directory is set
            if audio_config and self.audio_dir:
                try:
                    self.logger.info(f"Starting audio extraction for {video_path}")
                    audio_extractor = AudioExtractor(self.audio_dir)
                    success = audio_extractor.extract_audio(
                        input_path=video_path,
                        format=audio_config.get('format', 'mp3'),
                        bitrate=audio_config.get('bitrate', '192k'),
                        progress_callback=progress_callback
                    )
                    if success:
                        self.logger.info(f"Successfully extracted audio from {video_path}")
                    else:
                        self.logger.error(f"Failed to extract audio from {video_path}")
                except Exception as audio_error:
                    self.logger.error(f"Error during audio extraction: {str(audio_error)}")
            else:
                self.logger.info(f"Skipping audio extraction: audio_config={audio_config}, audio_dir={self.audio_dir}")

        except Exception as e:
            self.logger.error(f"Error processing video file {video_path}: {str(e)}")
            raise

    def _process_url(self, url: str, extraction_config: Dict, audio_config: Dict, progress_callback=None):
        try:
            # Extract audio directly from the URL if configured
            if audio_config and self.audio_dir:  # Check for audio_dir
                audio_extractor = AudioExtractor(self.audio_dir)  # Use self.audio_dir instead of output_dir
                audio_extractor.extract_audio(url, progress_callback=progress_callback, **audio_config)

            # Extract frames from the URL
            ydl_opts = {
                'format': 'best[ext=mp4]',
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_url = info['url']
                
            cap = cv2.VideoCapture(video_url)
            if not cap.isOpened():
                raise Exception(f"Could not open video stream: {url}")
            
            extractor = self._get_frame_extractor(extraction_config)
            if extractor:
                frames_extracted = extractor.extract_frames(cap, progress_callback)
                self.logger.info(f"Extracted {frames_extracted} frames from {url}")
            
            cap.release()
        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {str(e)}")

    def __del__(self):
        """Cleanup method"""
        try:
            cv2.destroyAllWindows()
        except:
            pass
