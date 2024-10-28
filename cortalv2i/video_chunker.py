# video_chunker.py
import cv2
import os
import logging
from typing import List, Tuple

class VideoChunker:
    def __init__(self, chunk_duration: int = 1200):  # 1200 seconds = 20 minutes
        self.chunk_duration = chunk_duration
        self.logger = logging.getLogger(self.__class__.__name__)

    def split_video(self, video_path: str, output_dir: str) -> List[str]:
        """Split video into chunks of specified duration"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"Could not open video: {video_path}")

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps
            
            if duration <= self.chunk_duration:
                cap.release()
                return [video_path]

            # Calculate chunks
            frames_per_chunk = int(self.chunk_duration * fps)
            num_chunks = int(total_frames / frames_per_chunk) + 1
            
            # Get video codec and create output files
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            chunk_paths = []

            for chunk in range(num_chunks):
                chunk_path = os.path.join(output_dir, f"{base_name}_part{chunk+1}.mp4")
                chunk_paths.append(chunk_path)
                
                out = cv2.VideoWriter(
                    chunk_path,
                    fourcc,
                    fps,
                    (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), 
                     int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
                )

                frames_written = 0
                while frames_written < frames_per_chunk:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)
                    frames_written += 1
                
                out.release()

            cap.release()
            self.logger.info(f"Split video into {len(chunk_paths)} chunks")
            return chunk_paths

        except Exception as e:
            self.logger.error(f"Error splitting video: {str(e)}")
            if 'cap' in locals():
                cap.release()
            return [video_path]