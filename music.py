# music.py
from pathlib import Path
import random
import asyncio

async def add_random_music_to_results(result_folder, music_folder, overwrite_files, semaphore=None):
    """
    Накладывает случайную музыку из папки music на каждое видео в папке result, создавая новые файлы.
    """
    result_folder = Path(result_folder)
    music_folder = Path(music_folder)
    
    video_files = list(result_folder.glob('*.mp4'))
    music_files = list(music_folder.glob('*.[mM][pP]3')) + \
                  list(music_folder.glob('*.[wW][aA][vV]')) + \
                  list(music_folder.glob('*.[aA][aA][cC]'))
    
    if not music_files:
        print("Музыкальные файлы не найдены в папке music.")
        return
    
    if not video_files:
        print("Видео файлы не найдены в папке result для добавления музыки.")
        return
    
    semaphore = semaphore or asyncio.Semaphore(4)  # Ограничение по умолчанию: 4 параллельных процесса

    async def add_music_to_video(video_file, music_file, output_video):
        async with semaphore:
            print(f"Добавление музыки к {video_file.name} с использованием {music_file.name}")
            process = await asyncio.create_subprocess_exec(
                'ffmpeg',
                '-loglevel', 'error',
                '-i', str(video_file),
                '-i', str(music_file),
                '-c:v', 'copy',
                '-map', '0:v:0',
                '-map', '1:a:0',
                '-shortest',
                '-y' if overwrite_files else '-n',
                str(output_video),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                print(f"Ошибка при добавлении музыки к {video_file.name}: {stderr.decode()}")
            else:
                print(f"Музыка успешно добавлена к {video_file.name} как {output_video.name}")

    tasks = []
    for video_file in video_files:
        music_file = random.choice(music_files)
        output_video = result_folder / f"{video_file.stem}_music{video_file.suffix}"
        tasks.append(asyncio.create_task(add_music_to_video(video_file, music_file, output_video)))

    await asyncio.gather(*tasks)
