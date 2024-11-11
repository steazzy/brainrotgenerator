import os
import subprocess
import random
import uuid
from dotenv import load_dotenv
import glob
import argparse
import sys

# Load variables from .env file
load_dotenv()

# Retrieve variables from .env with the option to override via command-line arguments
parser = argparse.ArgumentParser(description="Combine videos with distraction videos and add music.")

parser.add_argument('--main_video', type=str, default=os.getenv('MAIN_VIDEO', 'main_video.mp4'),
                    help='Path to the main video file.')
parser.add_argument('--distraction_folder', type=str, default=os.getenv('DISTRACTION_FOLDER', 'distraction_videos'),
                    help='Folder containing distraction videos.')
parser.add_argument('--music_folder', type=str, default=os.getenv('MUSIC_FOLDER', 'music'),
                    help='Folder containing music files.')
parser.add_argument('--result_folder', type=str, default=os.getenv('RESULT_FOLDER', 'result'),
                    help='Folder to save the result videos.')
parser.add_argument('--low_quality', type=lambda x: (str(x).lower() == 'true'), default=os.getenv('LOW_QUALITY', 'False').lower() == 'true',
                    help='Whether to use low quality settings.')
parser.add_argument('--overwrite_files', type=lambda x: (str(x).lower() == 'true'), default=os.getenv('OVERWRITE_FILES', 'True').lower() == 'true',
                    help='Whether to overwrite existing files without prompting.')
parser.add_argument('--add_music', type=lambda x: (str(x).lower() == 'true'), default=os.getenv('ADD_MUSIC', 'True').lower() == 'true',
                    help='Whether to add random music to the result videos.')

args = parser.parse_args()

# Assigning variables
MAIN_VIDEO = args.main_video
DISTRACTION_FOLDER = args.distraction_folder
MUSIC_FOLDER = args.music_folder
RESULT_FOLDER = args.result_folder
LOW_QUALITY = args.low_quality
OVERWRITE_FILES = args.overwrite_files
ADD_MUSIC = args.add_music

def get_video_duration(video_path):
    """
    Retrieves the duration of a video using ffprobe.
    """
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    try:
        return float(result.stdout)
    except ValueError:
        raise Exception(f"Could not determine duration for video: {video_path}")

def create_distraction_video(duration, exclude_list=[]):
    """
    Creates a distraction video by concatenating multiple videos from the distraction_videos folder.
    """
    videos = [os.path.join(DISTRACTION_FOLDER, f) for f in os.listdir(DISTRACTION_FOLDER)
              if f.lower().endswith(('.mp4', '.mov', '.avi'))]
    
    if not videos:
        raise Exception(f"No distraction videos found in {DISTRACTION_FOLDER}.")

    used_videos = []
    total_duration = 0
    file_list = []

    while total_duration < duration:
        available_videos = [v for v in videos if v not in used_videos and v not in exclude_list]
        if not available_videos:
            # Reset the used videos list to allow reuse but avoid consecutive repetitions
            last_used = used_videos[-1] if used_videos else None
            used_videos = []
            available_videos = [v for v in videos if v != last_used and v not in exclude_list]
            if not available_videos:
                break
        video = random.choice(available_videos)
        # Avoid consecutive repetitions
        if used_videos and video == used_videos[-1]:
            continue
        used_videos.append(video)
        video_duration = get_video_duration(video)
        total_duration += video_duration
        file_list.append(f"file '{video}'\n")

    if not file_list:
        raise Exception("Not enough videos to create a distraction video without repetitions.")

    # Generate unique filenames for temporary files
    unique_id = str(uuid.uuid4())
    file_list_path = f'temp_distraction_list_{unique_id}.txt'
    distraction_output = f'temp_distraction_video_{unique_id}.mp4'

    # Write the list of files for concatenation
    with open(file_list_path, 'w') as f:
        f.writelines(file_list)

    # Command to create the concatenated distraction video
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', file_list_path,
    ]

    # Quality settings based on LOW_QUALITY
    if LOW_QUALITY:
        # Low quality for faster encoding
        command += ['-vf', 'scale=320:-2', '-preset', 'ultrafast', '-crf', '28']
    else:
        # Original quality
        command += ['-c', 'copy']

    # Overwrite files without prompting if OVERWRITE_FILES is True
    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [distraction_output]
    subprocess.run(command, check=True)

    # Remove the temporary file list
    os.remove(file_list_path)

    return distraction_output, used_videos

def ensure_folder_exists(folder_path):
    """
    Ensures that the specified folder exists; creates it if it does not.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")

def check_main_video():
    """
    Checks if the main video exists.
    """
    if not os.path.isfile(MAIN_VIDEO):
        raise FileNotFoundError(f"Main video not found: {MAIN_VIDEO}")

def check_folders_have_content():
    """
    Checks if the distraction and music folders have the required content.
    """
    # Check distraction videos
    distraction_videos = [f for f in os.listdir(DISTRACTION_FOLDER)
                          if f.lower().endswith(('.mp4', '.mov', '.avi'))]
    if not distraction_videos:
        raise Exception(f"No distraction videos found in {DISTRACTION_FOLDER}.")

    # If adding music, check music files
    if ADD_MUSIC:
        music_files = [f for f in os.listdir(MUSIC_FOLDER)
                       if f.lower().endswith(('.mp3', '.wav', '.aac'))]
        if not music_files:
            raise Exception(f"No music files found in {MUSIC_FOLDER}.")

def variant1(main_video):
    """
    Variant 1: Main video occupies the entire screen with two distraction videos in opposite corners (top-left and bottom-right).
    """
    main_duration = get_video_duration(main_video)

    distraction_video1, used_videos1 = create_distraction_video(main_duration)
    distraction_video2, used_videos2 = create_distraction_video(main_duration, exclude_list=used_videos1)

    output_video = os.path.join(RESULT_FOLDER, 'variant1.mp4')

    filter_complex = (
        '[1:v]scale=240:-2[dist1];'
        '[2:v]scale=240:-2[dist2];'
        '[0:v][dist1]overlay=10:10[tmp1];'
        '[tmp1][dist2]overlay=main_w-overlay_w-10:main_h-overlay_h-10[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video1,
        '-i', distraction_video2,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video1)
    os.remove(distraction_video2)

def variant5(main_video):
    """
    Variant 5: Mirror of Variant 1.
    Distraction videos are placed in the top-right and bottom-left corners.
    """
    main_duration = get_video_duration(main_video)

    distraction_video1, used_videos1 = create_distraction_video(main_duration)
    distraction_video2, used_videos2 = create_distraction_video(main_duration, exclude_list=used_videos1)

    output_video = os.path.join(RESULT_FOLDER, 'variant5.mp4')

    filter_complex = (
        '[1:v]scale=240:-2[dist1];'
        '[2:v]scale=240:-2[dist2];'
        # Overlay dist1 in the top-right corner
        '[0:v][dist1]overlay=main_w-overlay_w-10:10[tmp1];'
        # Overlay dist2 in the bottom-left corner
        '[tmp1][dist2]overlay=10:main_h-overlay_h-10[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video1,
        '-i', distraction_video2,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video1)
    os.remove(distraction_video2)

def variant2(main_video):
    """
    Variant 2: Main video on the left, distraction video on the right, plus a small floating video in the top-left corner.
    """
    main_duration = get_video_duration(main_video)

    distraction_video1, used_videos1 = create_distraction_video(main_duration)
    distraction_video2, used_videos2 = create_distraction_video(main_duration, exclude_list=used_videos1)

    output_video = os.path.join(RESULT_FOLDER, 'variant2.mp4')

    # Set fixed sizes for the main videos
    target_width = 540
    target_height = 960

    filter_complex = (
        # Scale and align the main video
        f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
        f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
        # Scale and align the distraction video
        f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
        f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
        # Stack horizontally
        '[main][dist]hstack=inputs=2[tmp];'
        # Scale the floating video to a fixed size
        '[2:v]scale=135:-2[overlay];'
        # Overlay the floating video
        '[tmp][overlay]overlay=10:10[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video1,
        '-i', distraction_video2,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video1)
    os.remove(distraction_video2)

def variant6(main_video):
    """
    Variant 6: Mirror of Variant 2.
    Main video on the right, distraction video on the left, plus a small floating video in the top-right corner.
    """
    main_duration = get_video_duration(main_video)

    distraction_video1, used_videos1 = create_distraction_video(main_duration)
    distraction_video2, used_videos2 = create_distraction_video(main_duration, exclude_list=used_videos1)

    output_video = os.path.join(RESULT_FOLDER, 'variant6.mp4')

    # Set fixed sizes
    target_width = 540
    target_height = 960

    filter_complex = (
        # Scale and align the distraction video
        f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
        f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
        # Scale and align the main video
        f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,'
        f'pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
        # Stack horizontally
        '[dist][main]hstack=inputs=2[tmp];'
        # Scale the floating video to a fixed size
        '[2:v]scale=135:-2[overlay];'
        # Overlay the floating video in the top-right corner
        '[tmp][overlay]overlay=main_w-overlay_w-10:10[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video1,
        '-i', distraction_video2,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video1)
    os.remove(distraction_video2)

def variant3(main_video):
    """
    Variant 3: Distraction video is overlaid in the top-left corner.
    """
    main_duration = get_video_duration(main_video)

    distraction_video, used_videos = create_distraction_video(main_duration)

    output_video = os.path.join(RESULT_FOLDER, 'variant3.mp4')

    filter_complex = (
        '[1:v]scale=270:-2[overlay];'
        '[0:v][overlay]overlay=10:10[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video)

def variant7(main_video):
    """
    Variant 7: Mirror of Variant 3.
    Distraction video is overlaid in the top-right corner.
    """
    main_duration = get_video_duration(main_video)

    distraction_video, used_videos = create_distraction_video(main_duration)

    output_video = os.path.join(RESULT_FOLDER, 'variant7.mp4')

    filter_complex = (
        '[1:v]scale=270:-2[overlay];'
        '[0:v][overlay]overlay=main_w-overlay_w-10:10[out]'  # Overlay in the top-right corner
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video)

# New functions variant4 and variant8 without floating video

def variant4(main_video):
    """
    Variant 4: Main video on the left, distraction video on the right. No floating video.
    """
    main_duration = get_video_duration(main_video)

    distraction_video, used_videos = create_distraction_video(main_duration)

    output_video = os.path.join(RESULT_FOLDER, 'variant4.mp4')

    # Set fixed sizes for the main videos
    target_width = 540
    target_height = 960

    filter_complex = (
        f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
        f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
        '[main][dist]hstack=inputs=2[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video)

def variant8(main_video):
    """
    Variant 8: Main video on the right, distraction video on the left. No floating video.
    """
    main_duration = get_video_duration(main_video)

    distraction_video, used_videos = create_distraction_video(main_duration)

    output_video = os.path.join(RESULT_FOLDER, 'variant8.mp4')

    # Set fixed sizes for the main videos
    target_width = 540
    target_height = 960

    filter_complex = (
        f'[1:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[dist];'
        f'[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[main];'
        '[dist][main]hstack=inputs=2[out]'
    )

    command = [
        'ffmpeg',
        '-i', main_video,
        '-i', distraction_video,
        '-filter_complex', filter_complex,
        '-map', '[out]',
        '-map', '0:a?',
        '-shortest',
    ]

    if OVERWRITE_FILES:
        command += ['-y']
    else:
        command += ['-n']

    command += [output_video]
    subprocess.run(command, check=True)

    os.remove(distraction_video)

def cleanup_temp_files():
    """
    Removes all temporary files matching temp_distraction_video_*.mp4 from the current directory.
    """
    temp_files = glob.glob('temp_distraction_video_*.mp4')
    for temp_file in temp_files:
        os.remove(temp_file)
    print("Temporary files removed.")

def add_random_music_to_results():
    """
    Overlays random music from the music folder onto each video in the result folder, creating new files.
    """
    video_files = [f for f in os.listdir(RESULT_FOLDER) if f.lower().endswith('.mp4')]
    music_files = [os.path.join(MUSIC_FOLDER, f) for f in os.listdir(MUSIC_FOLDER)
                   if f.lower().endswith(('.mp3', '.wav', '.aac'))]

    if not music_files:
        print("No music files found in the music folder.")
        return

    if not video_files:
        print("No video files found in the result folder to add music to.")
        return

    for video_file in video_files:
        video_path = os.path.join(RESULT_FOLDER, video_file)
        music_file = random.choice(music_files)
        # Append suffix '_music' to the filename
        base_name, ext = os.path.splitext(video_file)
        output_video = os.path.join(RESULT_FOLDER, f"{base_name}_music{ext}")

        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', music_file,
            '-c:v', 'copy',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
        ]

        if OVERWRITE_FILES:
            command += ['-y']
        else:
            command += ['-n']

        command += [output_video]
        subprocess.run(command, check=True)

        print(f"Added music to {video_file}, saved as {base_name}_music{ext}")

def main():
    # Ensure all necessary folders exist
    ensure_folder_exists(DISTRACTION_FOLDER)
    if ADD_MUSIC:
        ensure_folder_exists(MUSIC_FOLDER)
    ensure_folder_exists(RESULT_FOLDER)

    # Check if the main video exists
    check_main_video()

    # Check if folders have the required content
    check_folders_have_content()

    # Execute all variants
    variant1(MAIN_VIDEO)
    variant2(MAIN_VIDEO)
    variant3(MAIN_VIDEO)
    variant4(MAIN_VIDEO)
    variant5(MAIN_VIDEO)
    variant6(MAIN_VIDEO)
    variant7(MAIN_VIDEO)
    variant8(MAIN_VIDEO)

    # Clean up temporary files
    cleanup_temp_files()

    # Add random music to result videos if ADD_MUSIC is True
    if ADD_MUSIC:
        add_random_music_to_results()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
