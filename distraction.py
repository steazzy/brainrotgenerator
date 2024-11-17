# distraction.py
from pathlib import Path
import subprocess
import random
import uuid
from utils import get_video_duration
import asyncio

async def create_distraction_video(duration, distraction_folder, low_quality, overwrite_files, exclude_list=[]):
    """
    Создает отвлекающее видео путем объединения нескольких видео из папки distraction_videos.
    """
    distraction_folder = Path(distraction_folder)
    videos = list(distraction_folder.glob('*.[mM][pP]4')) + \
             list(distraction_folder.glob('*.[mM][oO][vV]')) + \
             list(distraction_folder.glob('*.[aA][vV][iI]'))
    
    if not videos:
        raise Exception(f"В папке {distraction_folder} не найдено отвлекающих видео.")
    
    used_videos = []
    total_duration = 0
    file_list = []
    
    while total_duration < duration:
        available_videos = [v for v in videos if v not in used_videos and v not in exclude_list]
        if not available_videos:
            # Сброс списка использованных видео для разрешения повторений, но без подряд идущих
            last_used = used_videos[-1] if used_videos else None
            used_videos = []
            available_videos = [v for v in videos if v != last_used and v not in exclude_list]
            if not available_videos:
                break
        video = random.choice(available_videos)
        # Избежание повторений
        if used_videos and video == used_videos[-1]:
            continue
        used_videos.append(video)
        video_duration = get_video_duration(video)
        total_duration += video_duration
        file_list.append(f"file '{video}'\n")
    
    if not file_list:
        raise Exception("Недостаточно видео для создания отвлекающего видео без повторений.")
    
    # Генерация уникальных имен для временных файлов
    unique_id = uuid.uuid4()
    file_list_path = Path(f'temp_distraction_list_{unique_id}.txt')
    distraction_output = Path(f'temp_distraction_video_{unique_id}.mp4')
    
    # Запись списка файлов для объединения
    file_list_path.write_text(''.join(file_list), encoding='utf-8')
    
    # Команда для объединения видео
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(file_list_path),
    ]
    
    # Настройки качества
    if low_quality:
        # Низкое качество для ускорения кодирования
        command += ['-vf', 'scale=320:-2', '-preset', 'ultrafast', '-crf', '28']
    else:
        # Оригинальное качество
        command += ['-c:v', 'copy']
    
    # Параметры перезаписи файлов
    if overwrite_files:
        command += ['-y']
    else:
        command += ['-n']
    
    command += [str(distraction_output)]

    # Запуск FFmpeg в отдельном потоке, чтобы не блокировать основной поток
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"FFmpeg ошибка при создании отвлекающего видео: {stderr.decode()}")

    # Удаление временного списка файлов
    file_list_path.unlink()

    return distraction_output, used_videos
