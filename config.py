# config.py
from pathlib import Path
import argparse
from dotenv import load_dotenv
import os

def load_config():
    # Загрузка переменных из .env
    load_dotenv()
    
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Combine videos with distraction videos and add music.")
    
    parser.add_argument('--main_video', type=Path, default=Path(os.getenv('MAIN_VIDEO', 'main_video.mp4')),
                        help='Path to the main video file.')
    parser.add_argument('--distraction_folder', type=Path, default=Path(os.getenv('DISTRACTION_FOLDER', 'distraction_videos')),
                        help='Folder containing distraction videos.')
    parser.add_argument('--music_folder', type=Path, default=Path(os.getenv('MUSIC_FOLDER', 'music')),
                        help='Folder containing music files.')
    parser.add_argument('--result_folder', type=Path, default=Path(os.getenv('RESULT_FOLDER', 'result')),
                        help='Folder to save the result videos.')
    parser.add_argument('--low_quality', type=lambda x: (str(x).lower() == 'true'),
                        default=os.getenv('LOW_QUALITY', 'False').lower() == 'true',
                        help='Whether to use low quality settings.')
    parser.add_argument('--overwrite_files', type=lambda x: (str(x).lower() == 'true'),
                        default=os.getenv('OVERWRITE_FILES', 'True').lower() == 'true',
                        help='Whether to overwrite existing files without prompting.')
    parser.add_argument('--add_music', type=lambda x: (str(x).lower() == 'true'),
                        default=os.getenv('ADD_MUSIC', 'True').lower() == 'true',
                        help='Whether to add random music to the result videos.')
    parser.add_argument('--hwaccel', type=str, default=os.getenv('HWACCEL', 'none'),
                        choices=['none', 'qsv'],
                        help='Hardware acceleration method to use (none, qsv).')
    
    args = parser.parse_args()
    
    # Возвращение аргументов
    return args
