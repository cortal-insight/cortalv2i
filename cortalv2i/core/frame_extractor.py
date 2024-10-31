import cv2
import os
import logging
import numpy as np
from abc import ABC, abstractmethod

class FrameExtractor(ABC):
    def __init__(self, output_dir, output_format='jpg', resolution=None):
        # Use the exact path provided without any additional nesting
        self.output_dir = output_dir
        self.output_format = output_format
        self.resolution = resolution
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def extract_frames(self, cap, progress_callback=None):
        pass

    def save_frame(self, frame, frame_count):
        try:
            if self.resolution:
                if isinstance(self.resolution, str):
                    width, height = map(int, self.resolution.split('*'))
                    self.resolution = (width, height)
                frame = cv2.resize(frame, self.resolution)
            
            filename = f"frame_{frame_count:06d}.{self.output_format}"
            output_path = os.path.join(self.output_dir, filename)
            
            if self.output_format.lower() in ['jpg', 'jpeg']:
                cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            else:
                cv2.imwrite(output_path, frame)
            return True
        except Exception as e:
            self.logger.exception(f"Error saving frame: {str(e)}")
            return False

class FPSFrameExtractor(FrameExtractor):
    def __init__(self, output_dir, fps, **kwargs):
        super().__init__(output_dir, **kwargs)
        self.fps = fps

    def extract_frames(self, cap, progress_callback=None):
        frame_count = 0
        frames_extracted = 0
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(video_fps / self.fps)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                if self.save_frame(frame, frames_extracted):
                    frames_extracted += 1
            
            frame_count += 1
            if progress_callback:
                progress_callback(frame_count / total_frames)
        
        return frames_extracted

class TimeIntervalFrameExtractor(FrameExtractor):
    def __init__(self, output_dir, time_interval, **kwargs):
        super().__init__(output_dir, **kwargs)
        self.time_interval = time_interval

    def extract_frames(self, cap, progress_callback=None):
        frame_count = 0
        frames_extracted = 0
        prev_timestamp = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if current_timestamp - prev_timestamp >= self.time_interval:
                if self.save_frame(frame, frames_extracted):
                    frames_extracted += 1
                prev_timestamp = current_timestamp
            
            frame_count += 1
            if progress_callback:
                progress_callback(frame_count / total_frames)
        
        return frames_extracted

class ChangeDetectionFrameExtractor(FrameExtractor):
    def __init__(self, output_dir, threshold, min_area=500, **kwargs):
        super().__init__(output_dir, **kwargs)
        self.threshold = threshold
        self.min_area = min_area

    def extract_frames(self, cap, progress_callback=None):
        frame_count = 0
        frames_extracted = 0
        prev_frame = None
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if prev_frame is None:
                prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                continue
            
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame_delta = cv2.absdiff(prev_frame, gray_frame)
            thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            total_change_area = sum(cv2.contourArea(c) for c in contours)
            frame_area = gray_frame.shape[0] * gray_frame.shape[1]
            change_percentage = total_change_area / frame_area
            
            if change_percentage >= self.threshold and total_change_area >= self.min_area:
                if self.save_frame(frame, frames_extracted):
                    frames_extracted += 1
            
            prev_frame = gray_frame
            frame_count += 1
            if progress_callback:
                progress_callback(frame_count / total_frames)
        
        return frames_extracted
