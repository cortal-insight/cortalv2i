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
    def __init__(self, output_dir: str, max_workers: int = None):
        self.output_dir = output_dir
        self.max_workers = max_workers or os.cpu_count()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Create output directories
        self.frame_output_dir = os.path.join(output_dir, 'frames')
        self.audio_output_dir = os.path.join(output_dir, 'audio')
        os.makedirs(self.frame_output_dir, exist_ok=True)
        os.makedirs(self.audio_output_dir, exist_ok=True)

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
                    self.frame_output_dir,
                    fps=params['fps'],
                    output_format=output_format,
                    resolution=resolution
                )
            elif method == "2" and params.get('time_interval'):
                return TimeIntervalFrameExtractor(
                    self.frame_output_dir,
                    time_interval=params['time_interval'],
                    output_format=output_format,
                    resolution=resolution
                )
            elif method == "3" and params.get('threshold'):
                return ChangeDetectionFrameExtractor(
                    self.frame_output_dir,
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
            # Extract frames
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"Could not open video file: {video_path}")
            
            extractor = self._get_frame_extractor(extraction_config)
            if extractor:
                frames_extracted = extractor.extract_frames(cap, progress_callback)
                self.logger.info(f"Extracted {frames_extracted} frames from {video_path}")
            
            cap.release()

            # Extract audio if configured
            if audio_config:
                audio_extractor = AudioExtractor(self.audio_output_dir)
                audio_extractor.extract_audio(video_path, progress_callback=progress_callback, **audio_config)
        except Exception as e:
            self.logger.error(f"Error processing video file {video_path}: {str(e)}")

    def _process_url(self, url: str, extraction_config: Dict, audio_config: Dict, progress_callback=None):
        try:
            # Extract audio directly from the URL if configured
            if audio_config:
                audio_extractor = AudioExtractor(self.audio_output_dir)
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