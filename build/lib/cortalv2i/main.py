import os
from video_processor import process_videos

def main():
    input_path = input("Enter the directory of video files or path to text file with YouTube links: ").strip()
    output_dir = input("Enter the output directory for images: ").strip()
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    process_videos(input_path, output_dir)

if __name__ == "__main__":
    main()