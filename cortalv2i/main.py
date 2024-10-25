import logging
import os
import sys
from typing import List, Dict
from pathlib import Path
import cv2
from tqdm import tqdm
from cortalv2i.video_processor import VideoProcessor
from cortalv2i.audio_extractor import AudioExtractor

def setup_logging(log_file: str = 'video_processing.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_video_duration(video_path: str) -> int:
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = int(frame_count / fps)
        cap.release()
        return duration
    except:
        return 0

def process_input_source(source: str) -> List[str]:
    if os.path.isfile(source):
        if source.endswith(('.txt', '.csv')):
            with open(source, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        elif source.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
            return [source]
    elif os.path.isdir(source):
        return [str(p) for p in Path(source).glob('**/*') if p.suffix.lower() in ('.mp4', '.avi', '.mkv', '.mov')]
    elif source.startswith(('http://', 'https://', 'www.')):
        return [source]
    return []

def calculate_workers(video_length_seconds: int) -> int:
    if video_length_seconds < 300:
        return 2
    elif video_length_seconds < 1800:
        return 4
    else:
        return min(8, os.cpu_count() or 1)

def process_with_progress(processor, source: str, config: Dict, process_type: str):
    duration = get_video_duration(source) if os.path.isfile(source) else 100
    with tqdm(total=duration, desc=f"{process_type} {os.path.basename(source)}",
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
        def progress_callback(progress):
            pbar.n = int(progress * duration)
            pbar.refresh()
        
        if process_type == "Extracting frames from":
            processor.process_input(source, config, progress_callback=progress_callback)
        elif process_type == "Extracting audio from":
            processor.extract_audio(source, progress_callback=progress_callback, **config)

def get_user_input(prompt: str, default: str = '', validator=None):
    while True:
        user_input = input(f"{prompt} [default: {default}]: ").strip() or default
        if validator is None or validator(user_input):
            return user_input
        print("Invalid input. Please try again.")

def get_paths():
    print("\n=== Path Selection ===")
    input_path = get_user_input("\nEnter input path (video file/folder/URL/text file)", 
                                validator=lambda x: os.path.exists(x) or x.startswith(('http://', 'https://', 'www.')))
    output_path = get_user_input("\nEnter output directory path", 'output')
    os.makedirs(output_path, exist_ok=True)
    return input_path, output_path

def get_processing_options():
    print("\n=== Video Processing Options ===")
    
    method = get_user_input("\nSelect frame extraction method:\n1. FPS-based\n2. Time interval-based\n3. Change detection-based\nEnter your choice (1-3)", 
                            "1", lambda x: x in ["1", "2", "3"])
    
    params = {}
    if method == "1":
        params['fps'] = int(get_user_input("Enter frames per second (1-60)", "1", lambda x: 1 <= int(x) <= 60))
    elif method == "2":
        params['time_interval'] = float(get_user_input("Enter time interval in seconds (0.1-60)", "5", lambda x: 0.1 <= float(x) <= 60))
    elif method == "3":
        params['threshold'] = float(get_user_input("Enter change detection threshold (0.0-1.0)", "0.3", lambda x: 0.0 <= float(x) <= 1.0))

    print("\n=== Image Output Options ===")
    image_format = "jpg" if get_user_input("Select image format (1: jpg, 2: png)", "1", lambda x: x in ["1", "2"]) == "1" else "png"
    
    resolution = get_user_input("Enter resolution (e.g., 1920*1080 or press Enter for original)")
    if resolution:
        try:
            resolution = tuple(map(int, resolution.split('*')))
        except:
            print("Invalid resolution format. Using original resolution.")
            resolution = None

    print("\n=== Audio Options ===")
    extract_audio = get_user_input("Extract audio? (y/n)", "n").lower() == 'y'
    audio_config = None
    if extract_audio:
        audio_format = {"1": "mp3", "2": "wav", "3": "aac"}[get_user_input("Select audio format (1: mp3, 2: wav, 3: aac)", "1", lambda x: x in ["1", "2", "3"])]
        bitrate = {"1": "128k", "2": "192k", "3": "320k"}[get_user_input("Select bitrate (1: 128k, 2: 192k, 3: 320k)", "2", lambda x: x in ["1", "2", "3"])]
        audio_config = {'format': audio_format, 'bitrate': bitrate}

    return {
        'method': method,
        'params': params,
        'output_format': image_format,
        'resolution': resolution,
        'audio': audio_config
    }

def main():
    try:
        input_path, output_path = get_paths()
        frames_dir = os.path.join(output_path, 'frames')
        audio_dir = os.path.join(output_path, 'audio')
        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)

        setup_logging(os.path.join(output_path, 'processing.log'))
        logger = logging.getLogger(__name__)

        preferences = get_processing_options()

        input_sources = process_input_source(input_path)
        if not input_sources:
            logger.error(f"No valid input sources found from: {input_path}")
            return

        for source in input_sources:
            logger.info(f"\nProcessing: {source}")
            video_length = get_video_duration(source)
            max_workers = calculate_workers(video_length)

            processor = VideoProcessor(frames_dir, max_workers=max_workers)
            process_with_progress(processor, source, preferences, "Extracting frames from")

            if preferences['audio']:
                audio_extractor = AudioExtractor(audio_dir)
                process_with_progress(audio_extractor, source, preferences['audio'], "Extracting audio from")

        logger.info("\nProcessing completed successfully")
        print(f"\nProcessing completed successfully! Output files can be found in: {output_path}")

    except Exception as e:
        logger.exception(f"An error occurred during processing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()