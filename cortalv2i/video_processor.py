import os
import cv2
import yt_dlp
from tqdm import tqdm
from cortalv2i.frame_extractor import extract_frames_from_stream

def get_user_inputs(method):
    if method == '1':  # Frames per second
        fps = int(input("Enter frames per second to capture: "))
        return {'fps': fps}
    elif method == '2':  # Time interval
        time_interval = int(input("Enter time interval in seconds: "))
        return {'time_interval': time_interval}
    elif method == '3':  # Change detection
        threshold = float(input("Enter change detection threshold (0-1): "))
        return {'threshold': threshold}
    return {}

def stream_youtube_video(youtube_url, output_dir, method, user_inputs):
    ydl_opts = {
        'format': 'best',
        'quiet': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        video_url = info_dict['url']
    
    cap = cv2.VideoCapture(video_url)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    with tqdm(total=total_frames, desc=f"Processing {youtube_url}", unit="frame") as pbar:
        extract_frames_from_stream(cap, output_dir, method, user_inputs, pbar)

def process_videos(input_path, output_dir, method):
    user_inputs = get_user_inputs(method)

    if os.path.isfile(input_path):
        if input_path.endswith('.txt'):
            with open(input_path, 'r') as file:
                urls = file.readlines()
            for url in tqdm(urls, desc="Processing YouTube videos"):
                stream_youtube_video(url.strip(), output_dir, method, user_inputs)
        else:
            print(f"Processing video file: {input_path}")
            cap = cv2.VideoCapture(input_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            with tqdm(total=total_frames, desc=f"Processing {input_path}", unit="frame") as pbar:
                extract_frames_from_stream(cap, output_dir, method, user_inputs, pbar)
    elif os.path.isdir(input_path):
        video_files = [f for f in os.listdir(input_path) if f.endswith(('.mp4', '.avi', '.mov'))]
        for filename in tqdm(video_files, desc="Processing video files"):
            video_path = os.path.join(input_path, filename)
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            with tqdm(total=total_frames, desc=f"Processing {filename}", unit="frame", leave=False) as pbar:
                extract_frames_from_stream(cap, output_dir, method, user_inputs, pbar)
    else:
        print("Invalid input path. Please provide a valid directory, video file, or text file with YouTube links.")

# Example usage
if __name__ == "__main__":
    input_path = input("Enter the directory of video files or path to text file with YouTube links: ").strip()
    output_dir = input("Enter the output directory for images: ").strip()
    method = input("Choose method to capture images (1: Frames per second, 2: Time interval, 3: Change detection): ").strip()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    process_videos(input_path, output_dir, method)