#!/usr/local/bin/python3
import os
from pathlib import Path
import sys

import logbook
from tqdm import tqdm

logger = logbook.Logger(__name__)
logbook.StreamHandler(
    sys.stdout, level=logbook.DEBUG, bubble=True,
    format_string='[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}: {record.message}').push_application()


def main():
    """
    Rename all episodes in the given (or current) season directory, interactively based on user preferences.
    """
    path = Path(sys.argv[1] if len(sys.argv) == 2 else os.getcwd())
    logger.info(f'Starting episodes rename for path: {path}')
    if len(sys.argv) == 1:
        logger.debug('To use a different path than the current one, give it as a parameter')

    files_list = sorted(os.listdir(path))
    logger.info('Original files list ({}):\n{}'.format(len(files_list), '\n'.join(files_list)))

    guessed_show_name = path.parent.name
    show_name = input(f'Please enter the show\'s name [{guessed_show_name}]: ') or guessed_show_name
    guessed_season = path.name.rsplit(' ')[1]
    season = int(input(f'Please enter the season number [{guessed_season}]: ') or guessed_season)
    initial_episode = int(input(f'Optional - Enter an initial episode number to override current numbers (or click Enter to skip): ') or 0)
    if initial_episode == 0:
        numbers_before_episode = int(input(
            'Please enter the amount of numeric characters before the episode number [0]: ') or 0)
    dots_in_name = show_name.count('.')

    new_paths = []
    file_index = 0
    for file_name in tqdm(files_list):
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path):
            continue
        if initial_episode == 0:
            current_numbers_before_episode = numbers_before_episode
            episode_index = 0
            while not file_name[episode_index].isnumeric() or current_numbers_before_episode:
                if file_name[episode_index].isnumeric():
                    current_numbers_before_episode -= 1
                episode_index += 1
            episode = int(file_name[episode_index:episode_index + 2])
        else:
            episode = initial_episode + file_index

        extension = file_name.split('.', dots_in_name + 1)[dots_in_name + 1]
        new_name = f'{show_name} - S{season:02}E{episode:02}.{extension}'
        new_paths.append((full_path, os.path.join(path, new_name)))
        file_index += 1

    logger.info('New files list ({}):\n{}'.format(len(new_paths), '\n'.join([p[1] for p in new_paths])))
    should_rename = (input('Please approve this rename [y]: ') or 'y') == 'y'

    if should_rename:
        logger.info(f'Renaming {len(new_paths)} files...')
        for old_path, new_path in tqdm(new_paths):
            os.rename(old_path, new_path)
    else:
        logger.info('Skipped renaming.')

    logger.info('All done!')


if __name__ == '__main__':
    main()
