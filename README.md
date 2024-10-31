# Cortalv2i

A video processing and frame extraction SDK that supports multiple input sources and extraction methods.

## Features

- Multiple frame extraction methods (FPS-based, time-interval, change detection)
- Audio extraction support
- YouTube video processing
- Batch processing capabilities
- Progress tracking
- Parallel processing support

## Installation

bash
pip install cortalv2i
## Usage
python
from cortalv2i.video_processor import VideoProcessor
Initialize processor
processor = VideoProcessor(
frames_dir="output/frames",
audio_dir="output/audio"
)
Process a video file
processor.process_input(
"path/to/video.mp4",
extraction_config={
"method": "1",
"params": {"fps": 1},
"output_format": "jpg"
},
audio_config={
"format": "mp3",
"bitrate": "192k"
}
)

## commands
```
## steps to use this
clone this repo 
```
git clone https://github.com/cortal-ai/cortalv2i.git
```

# Extract frames only
python -m cortalv2i.extract_frames C:\Users\*username*\Downloads\cortal\input\video_1.mp4 C:\Users\*username*\Downloads\cortal\output\ --fps 1 --format jpg --resolution 1920*1080

## using config.yaml file
python -m cortalv2i.main --config config.yaml

## using interactive terminal
python -m cortalv2i.main

## License

This project is licensed under the MIT License - see the LICENSE file for details.