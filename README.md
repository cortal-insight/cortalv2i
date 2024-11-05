# Cortalv2i

A video processing and frame extraction SDK that supports multiple input sources and extraction methods.

### Features

- Multiple frame extraction methods (FPS-based, time-interval, change detection)
- Audio extraction support
- YouTube video processing
- Batch processing capabilities
- Progress tracking
- Parallel processing support

### Usage

1. Clone this repo 
```
git clone https://github.com/cortal-ai/cortalv2i.git
cd cortalinsight-example-workflows
```

2. Create a virtual environment for this project:
```
pyenv virtualenv 3.x.x test-env
pyenv activate test-env
```

3. Install the required dependencies:
```
pip install -r requirements.txt
```

### Extract frames only
To run the script and interactively select the options for frame extraction:
```
python main.py 
```

### Using config.yaml file
```
python main.py --config config.yaml
```

### Programmatic Usage

Import the VideoProcessor class from the cortalv2i library

```
from cortalv2i.core.video_processor import VideoProcessor
```

Initialize the Processor: 
```
processor = VideoProcessor(
frames_dir="output/frames",
audio_dir="output/audio"
)
```

Set configuration for processing:
```
frame_config = {
    "method": "fps",  # Extract frames based on frames per second
    "params": {"fps": 1},  # Extract 1 frame per second
    "output_format": "jpg",  # Save frames as JPG
    "resolution": "640*480"  # Resize frames to 640x480 resolution (optional)
}
```

Process the Input Video
```
# Define progress callback function
def progress_callback(progress):
    # Only log progress every 10% increment
    if progress_callback.last_logged is None or progress - progress_callback.last_logged >= 0.1:
        print(f"Progress: {progress * 100:0.0f}%")
        progress_callback.last_logged = progress

progress_callback.last_logged = None

# Process the input video
processor.process_input(
    input_source= "input/media.mp4",  # Path to the video file
    start_frame=0,  # Starting frame number
    end_frame=300,  # Ending frame number (process first 300 frames)
    extraction_config=frame_config,  # Frame extraction settings
    progress_callback=progress_callback  # Optional progress callback
)
```








### License
This project is licensed under the MIT License - see the LICENSE file for details.
