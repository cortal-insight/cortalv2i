import logging
import os
import sys
from typing import List, Dict
from pathlib import Path
import cv2
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from cortalv2i.video_processor import VideoProcessor
from cortalv2i.audio_extractor import AudioExtractor
from cortalv2i.dir_manage import DirectoryManager
from cortalv2i.video_chunker import VideoChunker

def setup_logging(log_file: str):
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

def process_video_chunk(chunk_path: str, frames_dir: str, audio_dir: str, 
                       preferences: Dict, max_workers: int, extract_audio: bool = True) -> None:
    """Process a single video chunk"""
    try:
        logger = logging.getLogger(__name__)
        
        # Log input parameters
        logger.info(f"Processing chunk: {chunk_path}")
        logger.info(f"Frames directory: {frames_dir}")
        logger.info(f"Audio directory: {audio_dir}")
        logger.info(f"Extract audio: {extract_audio}")
        
        # Create processor with both frames and audio directories
        processor = VideoProcessor(
            frames_dir=frames_dir,
            audio_dir=audio_dir if extract_audio else None,
            max_workers=max_workers
        )
        
        # Ensure audio config is properly formatted
        audio_config = None
        if extract_audio and preferences.get('audio'):
            audio_config = {
                'format': preferences['audio'].get('format', 'mp3'),
                'bitrate': preferences['audio'].get('bitrate', '192k')
            }
        
        # Create a progress bar wrapper
        with tqdm(total=100, desc=f"Processing {os.path.basename(chunk_path)}") as pbar:
            def progress_callback(progress):
                pbar.n = int(progress * 100)
                pbar.refresh()
            
            # Process the video
            processor.process_input(
                input_source=chunk_path,
                extraction_config=preferences,
                audio_config=audio_config,
                progress_callback=progress_callback
            )

    except Exception as e:
        logger.error(f"Error in process_video_chunk: {str(e)}")
        raise

def process_with_progress(processor, source: str, config: Dict, process_type: str):
    """Handle progress updates for processing"""
    try:
        # Don't try to get duration if source is None or not a file
        if source and os.path.isfile(source):
            duration = get_video_duration(source)
        else:
            duration = 100  # Default duration for progress bar
            
        with tqdm(total=duration, desc=f"{process_type}",
                  bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pbar:
            def progress_callback(progress):
                pbar.n = int(progress * duration)
                pbar.refresh()
            
            if processor and source:
                if process_type == "Extracting frames from":
                    processor.process_input(source, config, progress_callback=progress_callback)
                elif process_type == "Extracting audio from":
                    processor.extract_audio(source, progress_callback=progress_callback, **config)
            else:
                # Just update progress bar
                pbar.n = int(progress * duration)
                pbar.refresh()
                
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in progress handling: {str(e)}")

def get_user_input(prompt: str, default: str = '', validator=None):
    while True:
        user_input = input(f"{prompt} [default: {default}]: ").strip() or default
        if validator is None or validator(user_input):
            return user_input
        print("Invalid input. Please try again.")

def get_paths():
    """Get input and output paths from user"""
    print("\n=== Path Selection ===")
    
    # Get input path
    while True:
        input_path = input("\nEnter input path (video file/folder/URL/text file): ").strip()
        if os.path.exists(input_path) or input_path.startswith(('http://', 'https://', 'www.')):
            break
        print("Invalid path. Please enter a valid file/folder path or URL.")
    
    # Get output path
    while True:
        output_path = input("\nEnter output directory path: ").strip()
        try:
            os.makedirs(output_path, exist_ok=True)
            break
        except Exception as e:
            print(f"Error creating output directory: {str(e)}")
            print("Please enter a valid directory path.")
    
    return input_path, output_path

def get_processing_options():
    """Get processing options from user"""
    print("\n=== Processing Options ===")
    options = {}
    
    # Frame extraction method
    print("\nSelect frame extraction method:")
    print("1. FPS-based extraction")
    print("2. Time interval-based extraction")
    print("3. Change detection-based extraction")
    
    while True:
        method = input("Enter your choice (1-3): ").strip()
        if method in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    # Get parameters based on method
    if method == "1":
        while True:
            try:
                fps = float(input("Enter desired FPS (e.g., 1 for 1 frame per second): "))
                if fps > 0:
                    options['frames'] = {
                        'method': method,
                        'params': {'fps': fps}
                    }
                    break
            except ValueError:
                print("Please enter a valid number.")
    
    elif method == "2":
        while True:
            try:
                interval = float(input("Enter time interval in seconds: "))
                if interval > 0:
                    options['frames'] = {
                        'method': method,
                        'params': {'time_interval': interval}
                    }
                    break
            except ValueError:
                print("Please enter a valid number.")
    
    elif method == "3":
        while True:
            try:
                threshold = float(input("Enter change detection threshold (0.0-1.0): "))
                if 0 <= threshold <= 1:
                    options['frames'] = {
                        'method': method,
                        'params': {'threshold': threshold}
                    }
                    break
            except ValueError:
                print("Please enter a valid number between 0 and 1.")
    
    # Frame format
    print("\nSelect frame format:")
    print("1. JPG")
    print("2. PNG")
    while True:
        format_choice = input("Enter your choice (1-2): ").strip()
        if format_choice in ['1', '2']:
            options['frames']['output_format'] = 'jpg' if format_choice == '1' else 'png'
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    # Resolution (optional)
    print("\nEnter desired resolution (leave blank for original resolution)")
    print("Format: width*height (e.g., 1920*1080)")
    res = input("Resolution: ").strip()
    if res:
        options['frames']['resolution'] = res
    
    # Audio extraction
    while True:
        audio_choice = input("\nExtract audio? (y/n): ").strip().lower()
        if audio_choice in ['y', 'n']:
            break
        print("Please enter 'y' or 'n'.")
    
    if audio_choice == 'y':
        # Audio format
        print("\nSelect audio format:")
        print("1. MP3")
        print("2. WAV")
        print("3. AAC")
        while True:
            format_choice = input("Enter your choice (1-3): ").strip()
            if format_choice in ['1', '2', '3']:
                format_map = {'1': 'mp3', '2': 'wav', '3': 'aac'}
                audio_format = format_map[format_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        
        # Audio bitrate
        print("\nSelect audio bitrate:")
        print("1. 128k")
        print("2. 192k")
        print("3. 320k")
        while True:
            bitrate_choice = input("Enter your choice (1-3): ").strip()
            if bitrate_choice in ['1', '2', '3']:
                bitrate_map = {'1': '128k', '2': '192k', '3': '320k'}
                bitrate = bitrate_map[bitrate_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        
        options['audio'] = {
            'format': audio_format,
            'bitrate': bitrate
        }
    
    return options

def get_user_input():
    """Get input sources from user"""
    print("\nWelcome to Cortal Video Processor!")
    print("Please enter your video source(s). It can be:")
    print("1. A path to a video file")
    print("2. A path to a directory containing videos")
    print("3. A path to a text file containing video paths/URLs")
    print("4. A direct video URL")
    print("\nEnter 'done' when finished adding sources.")
    
    sources = []
    while True:
        source = input("\nEnter source path/URL (or 'done' to finish): ").strip()
        if source.lower() == 'done':
            break
        if source:
            sources.append(source)
    
    return sources

def get_user_preferences():
    """Get all processing preferences from user"""
    preferences = {}
    
    print("\nWelcome to Cortal Video Processor!")
    
    # Get input path
    while True:
        input_path = input("\nEnter input path (video file/directory/text file with paths): ").strip()
        if os.path.exists(input_path):
            break
        print("Invalid path. Please enter a valid file or directory path.")
    
    # Get output directory
    while True:
        output_path = input("\nEnter output directory path: ").strip()
        try:
            os.makedirs(output_path, exist_ok=True)
            break
        except:
            print("Invalid output path. Please enter a valid directory path.")
    
    # Frame extraction method
    print("\nSelect frame extraction method:")
    print("1. FPS-based extraction")
    print("2. Time interval-based extraction")
    print("3. Change detection-based extraction")
    
    while True:
        method = input("Enter your choice (1-3): ").strip()
        if method in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")
    
    # Frame extraction parameters
    if method == '1':
        while True:
            try:
                fps = float(input("\nEnter desired FPS (e.g., 1 for 1 frame per second): "))
                if fps > 0:
                    preferences['frames'] = {
                        'method': 'fps',
                        'params': {'fps': fps}
                    }
                    break
            except ValueError:
                print("Please enter a valid number.")
    
    elif method == '2':
        while True:
            try:
                interval = float(input("\nEnter time interval in seconds: "))
                if interval > 0:
                    preferences['frames'] = {
                        'method': 'interval',
                        'params': {'interval': interval}
                    }
                    break
            except ValueError:
                print("Please enter a valid number.")
    
    else:  # method == '3'
        while True:
            try:
                threshold = float(input("\nEnter change detection threshold (0.0-1.0): "))
                if 0 <= threshold <= 1:
                    preferences['frames'] = {
                        'method': 'change',
                        'params': {'threshold': threshold}
                    }
                    break
            except ValueError:
                print("Please enter a valid number between 0 and 1.")
    
    # Resolution
    print("\nEnter desired resolution (leave blank for original resolution)")
    print("Format: width*height (e.g., 1920*1080)")
    resolution = input("Resolution: ").strip()
    if resolution:
        preferences['frames']['resolution'] = resolution
    
    # Frame output format
    print("\nSelect frame output format:")
    print("1. JPG")
    print("2. PNG")
    while True:
        format_choice = input("Enter your choice (1-2): ").strip()
        if format_choice in ['1', '2']:
            preferences['frames']['output_format'] = 'jpg' if format_choice == '1' else 'png'
            break
        print("Invalid choice. Please enter 1 or 2.")
    
    # Audio extraction
    while True:
        audio_extract = input("\nExtract audio? (y/n): ").strip().lower()
        if audio_extract in ['y', 'n']:
            break
        print("Please enter 'y' or 'n'.")
    
    if audio_extract == 'y':
        # Audio format
        print("\nSelect audio format:")
        print("1. MP3")
        print("2. WAV")
        print("3. AAC")
        while True:
            format_choice = input("Enter your choice (1-3): ").strip()
            if format_choice in ['1', '2', '3']:
                audio_format = {'1': 'mp3', '2': 'wav', '3': 'aac'}[format_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        
        # Audio bitrate
        print("\nSelect audio bitrate:")
        print("1. 128k")
        print("2. 192k")
        print("3. 320k")
        while True:
            bitrate_choice = input("Enter your choice (1-3): ").strip()
            if bitrate_choice in ['1', '2', '3']:
                audio_bitrate = {'1': '128k', '2': '192k', '3': '320k'}[bitrate_choice]
                break
            print("Invalid choice. Please enter 1, 2, or 3.")
        
        preferences['audio'] = {
            'format': audio_format,
            'bitrate': audio_bitrate
        }
    
    return input_path, output_path, preferences

def main():
    try:
        # Setup logging
        setup_logging('processing.log')
        logger = logging.getLogger(__name__)

        # Get paths and processing options
        input_path, base_output_path = get_paths()
        processing_options = get_processing_options()
        
        # Initialize components
        dir_manager = DirectoryManager()
        video_chunker = VideoChunker()
        
        # Process input sources
        input_sources = process_input_source(input_path)
        
        if not input_sources:
            print("No valid input sources found. Exiting...")
            sys.exit(1)
            
        # Print detected sources and configuration
        print("\nDetected video sources:")
        for idx, source in enumerate(input_sources, 1):
            print(f"{idx}. {source}")
            
        print("\nProcessing configuration:")
        print(f"Output directory: {base_output_path}")
        print(f"Frame extraction: {processing_options['frames']['method']}")
        print(f"Frame format: {processing_options['frames']['output_format']}")
        if 'resolution' in processing_options['frames']:
            print(f"Resolution: {processing_options['frames']['resolution']}")
        if 'audio' in processing_options:
            print(f"Audio format: {processing_options['audio']['format']}")
            print(f"Audio bitrate: {processing_options['audio']['bitrate']}")
        
        # Confirm with user
        confirm = input("\nProceed with processing? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Processing cancelled by user.")
            sys.exit(0)

        # Process each source
        for source in input_sources:
            try:
                logger.info(f"\nProcessing: {source}")
                print(f"\nProcessing: {source}")
                
                # Get output paths for this source
                paths = dir_manager.get_output_paths(source, base_output_path)
                os.makedirs(paths['frames'], exist_ok=True)
                if 'audio' in processing_options:
                    os.makedirs(paths['audio'], exist_ok=True)
                
                # Create video processor
                processor = VideoProcessor(
                    frames_dir=paths['frames'],
                    audio_dir=paths['audio'] if 'audio' in processing_options else None
                )
                
                # Process the video
                processor.process_input(
                    source,
                    extraction_config=processing_options['frames'],
                    audio_config=processing_options.get('audio'),
                    progress_callback=lambda x: print(f"Progress: {x*100:.1f}%", end='\r')
                )
                
                print(f"\nCompleted processing: {source}")
                
            except Exception as e:
                logger.exception(f"Error processing {source}: {str(e)}")
                print(f"\nError processing {source}: {str(e)}")

        print(f"\nProcessing completed! Output files can be found in: {base_output_path}")

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        print(f"\nAn error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
