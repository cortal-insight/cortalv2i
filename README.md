# CortalV2I

A tool to extract frames from videos or YouTube links.

## Features

- Supports multiple input formats including archives and text files with YouTube links.
- Extracts frames based on time intervals or change detection.
- Supports multiple output image formats.

## Example_code

import os
from cortalv2i.video_processor import process_videos

def main():
    # Example: Processing a directory of video files
    input_path = "/path/to/video/directory"
    output_dir = "/path/to/output/images"
    method = "2"  # Using time interval method

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process the videos
    process_videos(input_path, output_dir, method)

    print(f"Frames extracted to {output_dir}")

if __name__ == "__main__":
    main()

## Installation

```bash
pip install .

