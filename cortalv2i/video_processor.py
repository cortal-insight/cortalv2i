import os
import cv2
import yt_dlp
from cortalv2i.frame_extractor import extract_frames_from_stream

def stream_youtube_video(youtube_url, output_dir):
    method = input("Choose method to capture images (1: FPS, 2: Interval (default), 3: Change detection): ").strip() or '2'
    image_format = input("Choose image format (jpeg (default), png, jpg, tiff): ").strip() or 'jpeg'
    
    ydl_opts = {
        'format': 'best',
        'quiet': True  
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=False)
        video_url = info_dict['url']
    
    cap = cv2.VideoCapture(video_url)
    extract_frames_from_stream(cap, output_dir, method, image_format)

def process_videos(input_path, output_dir):
    if os.path.isfile(input_path):
        with open(input_path, 'r') as file:
            urls = file.readlines()
        for url in urls:
            stream_youtube_video(url.strip(), output_dir)
    elif os.path.isdir(input_path):
        for filename in os.listdir(input_path):
            if filename.endswith(('.mp4', '.avi', '.mov')):
                video_path = os.path.join(input_path, filename)
                cap = cv2.VideoCapture(video_path)
                extract_frames_from_stream(cap, output_dir)