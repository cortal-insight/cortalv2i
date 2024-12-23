import cv2
import os
from scenedetect import detect_scenes

def save_scene_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    scene_list = detect_scenes(video_path)

    cap = cv2.VideoCapture(video_path)

    for i, (start_time, end_time) in enumerate(scene_list):
        start_frame = start_time.get_frames()
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        success, frame = cap.read()
        if success:
            image_filename = f"scene_{i}.jpg"
            image_filepath = os.path.join(output_folder, image_filename)
            cv2.imwrite(image_filepath, frame)

    cap.release()

# Example usage:
# video_file = 'path_to_video.mp4'
# output_dir = 'output_directory'
# save_scene_frames(video_file, output_dir)