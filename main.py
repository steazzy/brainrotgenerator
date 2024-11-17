# main.py
import sys
import asyncio
from config import load_config
from utils import ensure_folder_exists, check_main_video, check_folders_have_content
from variants import Variants
from music import add_random_music_to_results


async def main_async():
    # Загрузка конфигурации
    config = load_config()

    # Присвоение переменных
    main_video = config.main_video
    distraction_folder = config.distraction_folder
    music_folder = config.music_folder
    result_folder = config.result_folder
    low_quality = config.low_quality
    overwrite_files = config.overwrite_files
    add_music = config.add_music
    hwaccel = config.hwaccel  # Получение метода аппаратного ускорения

    # Убедиться, что все необходимые папки существуют
    ensure_folder_exists(distraction_folder)
    if add_music:
        ensure_folder_exists(music_folder)
    ensure_folder_exists(result_folder)

    # Проверка наличия основного видео
    check_main_video(main_video)

    # Проверка содержимого папок
    check_folders_have_content(distraction_folder, music_folder, add_music)

    # Создание семафора для ограничения количества параллельных процессов
    semaphore = asyncio.Semaphore(4)  # Например, максимум 4 параллельных процесса

    # Инициализация класса Variants с выбором аппаратного ускорения и семафором
    variants = Variants(
        main_video=main_video,
        distraction_folder=distraction_folder,
        result_folder=result_folder,
        low_quality=low_quality,
        overwrite_files=overwrite_files,
        hwaccel=hwaccel,
        semaphore=semaphore
    )

    # Создание списка задач для всех вариантов
    tasks = [
        asyncio.create_task(variants.variant1()),
        asyncio.create_task(variants.variant2()),
        asyncio.create_task(variants.variant3()),
        asyncio.create_task(variants.variant4()),
        asyncio.create_task(variants.variant5()),
        asyncio.create_task(variants.variant6()),
        asyncio.create_task(variants.variant7()),
        asyncio.create_task(variants.variant8()),
    ]

    # Запуск всех задач параллельно
    await asyncio.gather(*tasks)


    # Добавление музыки, если включено
    if add_music:
        await add_random_music_to_results(result_folder, music_folder, overwrite_files)


def main():
    try:
        asyncio.run(main_async())
    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
