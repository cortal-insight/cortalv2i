import argparse
import subprocess
import logging
import os
import sys
from typing import List, Dict, Tuple
from pathlib import Path
import cv2
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml

from core.video_processor import VideoProcessor
from core.audio_extractor import AudioExtractor
from utils.dir_manager import DirectoryManager
from core.video_chunker import VideoChunker
from utils.config_loader import load_config

def setup_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

def process_input_source(source: str) -> List[str]:
    """
    Process the input source and return a list of files/URLs to process.
    """
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

def process_chunk(chunk_info: dict) -> bool:
    """
    Process a video chunk for frame extraction.
    """
    try:
        source = chunk_info['source']
        start_frame, end_frame = chunk_info['chunk_path']
        output_dir = chunk_info['output_dir']
        config = chunk_info['config']
        
        processor = VideoProcessor(
            frames_dir=output_dir['frames'],
            audio_dir=output_dir['audio'] if 'audio' in config else None
        )

        with tqdm(total=end_frame - start_frame,
                  desc=f"Chunk {chunk_info['index']}/{chunk_info['total']}",
                  position=chunk_info['index']) as pbar:

            def update_progress(progress):
                pbar.n = int(progress * (end_frame - start_frame))
                pbar.refresh()

            processor.process_input(
                source,
                start_frame=start_frame,
                end_frame=end_frame,
                extraction_config=config['frames'],
                audio_config=config.get('audio'),
                progress_callback=update_progress
            )
        
        return True

    except Exception as e:
        print(f"\nError processing chunk {chunk_info['index']}: {str(e)}")
        return False

def process_audio_chunk(chunk_info: dict) -> bool:
    """
    Process an audio chunk for extraction.
    """
    try:
        source = chunk_info['source']
        start_time, end_time = chunk_info['chunk_path']
        output_dir = chunk_info['output_dir']
        config = chunk_info['config']
        
        audio_processor = AudioExtractor(output_dir['audio'])

        with tqdm(total=100,
                  desc=f"Audio Chunk {chunk_info['index']}/{chunk_info['total']}",
                  position=chunk_info['index']) as pbar:

            def update_progress(progress):
                pbar.n = int(progress * 100)
                pbar.refresh()

            audio_processor.extract_audio(
                source,
                format=config['audio']['format'],
                bitrate=config['audio']['bitrate'],
                progress_callback=update_progress,
                start_time=start_time,
                end_time=end_time,
                chunk_index=chunk_info['index'] if chunk_info['total'] > 1 else None
            )
        
        return True

    except Exception as e:
        print(f"\nError processing audio chunk {chunk_info['index']}: {str(e)}")
        return False

def get_paths() -> Tuple[str, str]:
    print("\nPath Configuration:")
    while True:
        input_path = input("Enter input path (video file/folder/URL): ").strip()
        if input_path:
            if os.path.exists(input_path) or input_path.startswith(('http://', 'https://', 'www.')):
                break
            print("Invalid path! Please enter a valid file path, directory, or URL")
        else:
            print("Input path cannot be empty")

    while True:
        output_path = input("Enter output directory path: ").strip()
        if output_path:
            try:
                os.makedirs(output_path, exist_ok=True)
                break
            except Exception as e:
                print(f"Error creating output directory: {str(e)}")
        else:
            print("Output path cannot be empty")

    return input_path, output_path

def get_processing_options() -> Dict:
    options = {}
    print("\nSelect processing options:")
    options['frames'] = get_frame_config()
    if input("Extract audio? (y/n): ").strip().lower() == 'y':
        options['audio'] = get_audio_config()
    return options


def check_ffmpeg(logger) -> None:
    """
    Verify ffmpeg is installed on the system
    """
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("ffmpeg is installed and functional.")
    except subprocess.CalledProcessError as e:
        logger.error("ffmpeg is installed but encountered an error: %s", e)
        print("\nError: ffmpeg is installed but encountered an error. Please check your ffmpeg installation.")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("ffmpeg is not installed or not found in PATH. Please install ffmpeg.")
        print("\nError: ffmpeg is not installed or not found in PATH. Please install ffmpeg.")
        sys.exit(1)
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        print("\nError: An unexpected error occurred. Please check your ffmpeg installation.")
        sys.exit(1)

def get_audio_config() -> Dict:
    """
    Get audio extraction configuration from the user.
    """
    config = {}
    supported_formats = ['mp3', 'wav', 'aac', 'm4a', 'flac']
    supported_bitrates = ['64k', '128k', '192k', '256k', '320k']
    
    while True:
        format_choice = input(f"Select audio format ({'/'.join(supported_formats)}) [mp3]: ").strip().lower()
        if format_choice in [''] + supported_formats:
            break
        print(f"Invalid format! Please select from {', '.join(supported_formats)}")
    config['format'] = format_choice if format_choice else 'mp3'

    while True:
        bitrate_choice = input(f"Select audio bitrate ({'/'.join(supported_bitrates)}) [192k]: ").strip().lower()
        if bitrate_choice in [''] + supported_bitrates:
            break
        print(f"Invalid bitrate! Please select from {', '.join(supported_bitrates)}")
    config['bitrate'] = bitrate_choice if bitrate_choice else '192k'

    return config

def get_frame_config() -> Dict:
    config = {'method': None, 'params': {}}
    print("\nFrame Extraction Configuration:")
    print("1. Extract by FPS")
    print("2. Extract by time interval")
    print("3. Extract every second")
    while True:
        choice = input("Select extraction method (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice! Please select 1, 2, or 3")

    if choice == '1':
        config['method'] = 'fps'
        while True:
            try:
                fps = float(input("Enter frames per second (e.g., 1): ").strip() or 1)
                if fps > 0:
                    break
                print("FPS must be greater than 0")
            except ValueError:
                print("Please enter a valid number")
        config['params']['fps'] = fps
    elif choice == '2':
        config['method'] = 'interval'
        while True:
            try:
                interval = float(input("Enter interval in seconds (e.g., 1): ").strip() or 1)
                if interval > 0:
                    break
                print("Interval must be greater than 0")
            except ValueError:
                print("Please enter a valid number")
        config['params']['interval'] = interval
    elif choice == '3':
        config['method'] = 'fps'
        config['params'] = {'fps': 1.0}  # One frame per second

    while True:
        format_choice = input("Select frame format (jpg/png) [jpg]: ").strip().lower()
        if format_choice in ['', 'jpg', 'png']:
            break
        print("Invalid format! Please select jpg or png")
    config['output_format'] = format_choice if format_choice else 'jpg'

    resolution = input("Enter output resolution (e.g., 1920*1080) [original]: ").strip()
    if resolution:
        config['resolution'] = resolution

    return config

def main():
    parser = argparse.ArgumentParser(description="Video Processing Tool")
    parser.add_argument("--config", help="Path to config.yaml file")
    parser.add_argument("--input", help="Input path (video file/folder/URL)")
    parser.add_argument("--output", help="Output directory path")
    args = parser.parse_args()

    try:
        setup_logging('Processing.log')
        logger = logging.getLogger(__name__)

        check_ffmpeg(logger)

        if args.config:
            config = load_config(args.config)
            input_path = config['input_path']
            base_output_path = config['output_path']
            processing_options = config['processing_options']
        elif args.input and args.output:
            input_path = args.input
            base_output_path = args.output
            processing_options = get_processing_options()
        else:
            input_path, base_output_path = get_paths()
            processing_options = get_processing_options()

        dir_manager = DirectoryManager()
        
        input_sources = process_input_source(input_path)
        
        if not input_sources:
            print("No valid input sources found. Exiting...")
            sys.exit(1)

        for source in input_sources:
            try:
                logger.info(f"\nProcessing: {source}")
                print(f"\nProcessing: {source}")

                paths = dir_manager.get_output_paths(source, base_output_path)
                os.makedirs(paths['frames'], exist_ok=True)

                chunker = VideoChunker(chunk_minutes=15)  # 15 minutes chunks
                chunk_ranges = chunker.split_video(source)

                print(f"\nProcessing {len(chunk_ranges)} chunks of 15 minutes each...")

                with ThreadPoolExecutor(max_workers=min(4, len(chunk_ranges))) as executor:
                    futures = []
                    for idx, chunk_range in enumerate(chunk_ranges):
                        futures.append(
                            executor.submit(
                                process_chunk,
                                {
                                    'source': source,
                                    'chunk_path': chunk_range,
                                    'output_dir': paths,
                                    'config': processing_options,
                                    'index': idx + 1,
                                    'total': len(chunk_ranges)
                                }
                            )
                        )

                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Chunk processing error: {str(e)}")

                print(f"\nCompleted processing: {source}")

                if 'audio' in processing_options:
                    
                    import ffmpeg
                    os.makedirs(paths['audio'], exist_ok=True)
                    
                    # Get video duration
                    probe = ffmpeg.probe(source)
                    duration = float(probe['format']['duration'])
                    
                    # Create audio chunks
                    chunk_duration = 15 * 60  # 15 minutes in seconds
                    audio_chunks = [(i * chunk_duration, min((i + 1) * chunk_duration, duration)) 
                                    for i in range(int(duration / chunk_duration) + 1)]

                    print(f"\nProcessing {len(audio_chunks)} audio chunks...")

                    with ThreadPoolExecutor(max_workers=min(4, len(audio_chunks))) as executor:
                        futures = []
                        for idx, chunk_range in enumerate(audio_chunks):
                            futures.append(
                                executor.submit(
                                    process_audio_chunk,
                                    {
                                        'source': source,
                                        'chunk_path': chunk_range,
                                        'output_dir': paths,
                                        'config': processing_options,
                                        'index': idx + 1,
                                        'total': len(audio_chunks)
                                    }
                                )
                            )

                        for future in as_completed(futures):
                            try:
                                future.result()
                            except Exception as e:
                                logger.error(f"Audio chunk processing error: {str(e)}")

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