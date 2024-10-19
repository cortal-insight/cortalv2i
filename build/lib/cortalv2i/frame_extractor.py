import cv2
import os

def save_frame(frame, output_dir, frame_number, image_format='jpeg'):
    filename = f"frame_{frame_number:04d}.{image_format}"
    cv2.imwrite(os.path.join(output_dir, filename), frame)

def extract_frames_from_stream(cap, output_dir, method='2', image_format='jpeg'):
    if method == '1':  # Frames per second
        fps = int(input("Enter frames per second to capture (default 1): ") or 1)
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(original_fps / fps)
    
    elif method == '2':  # Time interval
        time_interval = int(input("Enter time interval in seconds (default 10): ") or 10)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * time_interval)
    
    elif method == '3':  # Change detection (simple threshold-based approach)
        threshold = float(input("Enter change detection threshold (0-1, default 0.5): ") or 0.5)
    
    frame_number = 0
    saved_frame_number = 0
    
    prev_frame = None
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if method in ['1', '2']:
            if frame_number % frame_interval == 0:
                save_frame(frame, output_dir, saved_frame_number, image_format)
                saved_frame_number += 1
        
        elif method == '3':
            if prev_frame is not None:
                diff = cv2.absdiff(prev_frame, frame)
                non_zero_count = cv2.countNonZero(cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY))
                total_pixels = diff.shape[0] * diff.shape[1]
                change_ratio = non_zero_count / total_pixels
                
                if change_ratio > threshold:
                    save_frame(frame, output_dir, saved_frame_number, image_format)
                    saved_frame_number += 1
            
            prev_frame = frame.copy()
        
        frame_number += 1
    
    cap.release()