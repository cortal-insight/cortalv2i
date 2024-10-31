import argparse
import cv2
from tqdm import tqdm
from cortalv2i.core.video_processor import VideoProcessor
from cortalv2i.core.audio_extractor import AudioExtractor
from cortalv2i.utils.dir_manager import DirectoryManager

def extract_frames_command():
    parser = argparse.ArgumentParser(description="Extract frames from video")
    parser.add_argument("input_path", help="Path to input video file")
    parser.add_argument("output_path", help="Path to output directory")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames per second to extract")
    parser.add_argument("--format", choices=['jpg', 'png'], default='jpg', help="Output image format")
    parser.add_argument("--resolution", help="Output resolution (e.g., 1920*1080)")
    args = parser.parse_args()

    dir_manager = DirectoryManager()
    paths = dir_manager.get_output_paths(args.input_path, args.output_path)

    total_frames = get_total_frames(args.input_path)

    processor = VideoProcessor(frames_dir=paths['frames'])
    
    with tqdm(total=total_frames, desc="Extracting frames", unit="frame") as pbar:
        def update_progress(progress):
            pbar.update(int(progress * total_frames) - pbar.n)

        processor.process_input(
            args.input_path,
            start_frame=0,
            end_frame=total_frames,
            extraction_config={
                'method': 'fps',
                'params': {'fps': args.fps},
                'output_format': args.format,
                'resolution': args.resolution
            },
            progress_callback=update_progress
        )

    print(f"\nFrames extracted to: {paths['frames']}")

def extract_audio_command():
    parser = argparse.ArgumentParser(description="Extract audio from video")
    parser.add_argument("input_path", help="Path to input video file")
    parser.add_argument("output_path", help="Path to output directory")
    parser.add_argument("--format", choices=['mp3', 'wav', 'aac', 'm4a', 'flac'], default='mp3', help="Output audio format")
    parser.add_argument("--bitrate", choices=['64k', '128k', '192k', '256k', '320k'], default='192k', help="Output audio bitrate")
    args = parser.parse_args()

    dir_manager = DirectoryManager()
    paths = dir_manager.get_output_paths(args.input_path, args.output_path)

    audio_processor = AudioExtractor(paths['audio'])
    
    with tqdm(total=100, desc="Extracting audio", unit="%") as pbar:
        def update_progress(progress):
            pbar.update(int(progress * 100) - pbar.n)

        audio_processor.extract_audio(
            args.input_path,
            format=args.format,
            bitrate=args.bitrate,
            progress_callback=update_progress
        )

    print(f"\nAudio extracted to: {paths['audio']}")

def get_total_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return total_frames