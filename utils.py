# utils.py
from pathlib import Path
import subprocess

def get_video_duration(video_path):
    """
    Получает длительность видео с помощью ffprobe.
    """
    video_path = Path(video_path)
    result = subprocess.run(
        [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    try:
        return float(result.stdout)
    except ValueError:
        raise Exception(f"Не удалось определить длительность видео: {video_path}")

def ensure_folder_exists(folder_path):
    """
    Убеждается, что указанная папка существует; создает ее, если нет.
    """
    folder = Path(folder_path)
    if not folder.exists():
        folder.mkdir(parents=True)
        print(f"Создана папка: {folder}")

def check_main_video(main_video):
    """
    Проверяет, существует ли основное видео.
    """
    video = Path(main_video)
    if not video.is_file():
        raise FileNotFoundError(f"Основное видео не найдено: {video}")

def check_folders_have_content(distraction_folder, music_folder, add_music):
    """
    Проверяет, содержат ли папки нужные файлы.
    """
    distraction_folder = Path(distraction_folder)
    distraction_videos = list(distraction_folder.glob('*.[mM][pP]4')) + \
                         list(distraction_folder.glob('*.[mM][oO][vV]')) + \
                         list(distraction_folder.glob('*.[aA][vV][iI]'))
    if not distraction_videos:
        raise Exception(f"В папке {distraction_folder} не найдено отвлекающих видео.")
    
    if add_music:
        music_folder = Path(music_folder)
        music_files = list(music_folder.glob('*.[mM][pP]3')) + \
                      list(music_folder.glob('*.[wW][aA][vV]')) + \
                      list(music_folder.glob('*.[aA][aA][cC]'))
        if not music_files:
            raise Exception(f"В папке {music_folder} не найдено музыкальных файлов.")
