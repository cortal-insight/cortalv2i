import os
from cortalv2i.video_processor import process_videos

def main():
    input_path = input("Enter the directory of video files or path to text file with YouTube links: ").strip()
    output_dir = input("Enter the output directory for images: ").strip()
    method = input("Choose method to capture images (1: Frames per second, 2: Time interval, 3: Change detection): ").strip()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    process_videos(input_path, output_dir, method)

if __name__ == "__main__":
    main()