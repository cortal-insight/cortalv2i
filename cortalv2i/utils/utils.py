import os
import cv2
import logging
from typing import List, Union
from pathlib import Path

def setup_logging(filename: str) -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(filename),
            logging.StreamHandler()
        ]
    )

def get_video_duration(video_path: str) -> float:
    """
    Get duration of video in seconds
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count/fps
        
        cap.release()
        return duration
    except Exception as e:
        logging.error(f"Error getting video duration: {str(e)}")
        return 0

def calculate_workers(duration: float) -> int:
    """
    Calculate optimal number of workers based on video duration
    """
    if duration <= 0:
        return 1
    
    # Base calculation on video length
    if duration < 60:  # Less than 1 minute
        return 2
    elif duration < 300:  # Less than 5 minutes
        return 4
    elif duration < 900:  # Less than 15 minutes
        return 6
    else:
        return 8

def process_input_source(input_path: str) -> List[str]:
    """
    Process input source and return list of video files to process
    """
    sources = []
    
    if not input_path:
        return sources

    # Handle direct video file
    if os.path.isfile(input_path):
        if is_video_file(input_path):
            sources.append(input_path)
        elif input_path.endswith('.txt'):
            # Read video paths from text file
            try:
                with open(input_path, 'r') as f:
                    for line in f:
                        path = line.strip()
                        if path and is_video_file(path):
                            sources.append(path)
            except Exception as e:
                logging.error(f"Error reading text file: {str(e)}")
    
    # Handle directory
    elif os.path.isdir(input_path):
        for root, _, files in os.walk(input_path):
            for file in files:
                if is_video_file(file):
                    sources.append(os.path.join(root, file))
    
    return sources

def is_video_file(filepath: str) -> bool:
    """
    Check if file is a video based on extension
    """
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
    return Path(filepath).suffix.lower() in video_extensions

def validate_path(path: str) -> bool:
    """
    Validate if path exists and is accessible
    """
    try:
        return os.path.exists(path) and os.access(path, os.R_OK)
    except Exception:
        return False

def ensure_directory(directory: str) -> bool:
    """
    Ensure directory exists, create if it doesn't
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Error creating directory {directory}: {str(e)}")
        return False

def get_safe_filename(filename: str) -> str:
    """
    Convert filename to safe version by removing invalid characters
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename