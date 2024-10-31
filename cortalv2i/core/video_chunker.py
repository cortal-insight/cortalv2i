# video_chunker.py
import cv2
import os
import numpy as np
from typing import List, Tuple
import tempfile

class VideoChunker:
    def __init__(self, chunk_minutes: int = 15):
        """Initialize VideoChunker
        
        Args:
            chunk_minutes: Length of each chunk in minutes
        """
        self.chunk_minutes = chunk_minutes
        self.temp_dir = tempfile.mkdtemp()

    def get_video_info(self, video_path: str) -> Tuple[int, float, int, int]:
        """Get video information"""
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return total_frames, fps, width, height

    def split_video(self, video_path: str) -> List[Tuple[int, int]]:
        """Split video into frame ranges based on time chunks
        
        Returns:
            List of (start_frame, end_frame) tuples
        """
        total_frames, fps, _, _ = self.get_video_info(video_path)
        
        # Calculate frames per chunk (15 minutes = 900 seconds)
        frames_per_chunk = int(fps * self.chunk_minutes * 60)
        chunks = []
        
        for start_frame in range(0, total_frames, frames_per_chunk):
            end_frame = min(start_frame + frames_per_chunk, total_frames)
            chunks.append((start_frame, end_frame))
            
        return chunks