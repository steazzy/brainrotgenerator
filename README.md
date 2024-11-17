# Video Combiner

A Python script to generate brain rot videos.

## Installation

### Clone the repository:
```bash
git clone https://github.com/steazzy/brainrotgenerator
```

### Install dependencies:

- **`poetry install`:**


### Install FFmpeg:

- **Windows:** Download from [FFmpeg](https://ffmpeg.org/download.html) and add to PATH.
- **macOS:** 
  ```bash
  brew install ffmpeg
  ```
- **Linux:** 
  ```bash
  sudo apt install ffmpeg
  ```

## Usage

Fill up `.env` or use arguments

```bash
poetry run python main.py
```

### Arguments

- `--main_video`: Path to the main video file.
- `--distraction_folder`: Folder containing distraction videos.
- `--music_folder`: Folder containing music files.
- `--result_folder`: Folder to save the result videos.
- `--low_quality`: Use low quality settings (`True` or `False`).
- `--overwrite_files`: Overwrite existing files without prompting (`True` or `False`).
- `--add_music`: Add random music to the result videos (`True` or `False`).
