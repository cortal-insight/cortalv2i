# Cortalv2i

A video processing and frame extraction SDK that supports multiple input sources and extraction methods.

## Features

- Multiple frame extraction methods (FPS-based, time-interval, change detection)
- Audio extraction support
- YouTube video processing
- Batch processing capabilities
- Progress tracking
- Parallel processing support


## Usage

Clone this repo 

```
git clone https://github.com/cortal-ai/cortalv2i.git
```

# Extract frames only
python main.py 

Pick the options accordingly


## using config.yaml file
python -m cortalv2i.main --config config.yaml

```
from cortalv2i.video_processor import VideoProcessor
Initialize processor
processor = VideoProcessor(
frames_dir="output/frames",
audio_dir="output/audio"
)
```

Process a video file

```
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
```








## License
This project is licensed under the MIT License - see the LICENSE file for details.
