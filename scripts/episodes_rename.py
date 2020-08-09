#!/usr/local/bin/python3
import os
from pathlib import Path
import sys

import logbook

logger = logbook.Logger(__name__)
logbook.StreamHandler(sys.stdout, level=logbook.DEBUG, bubble=True).push_application()


def main():
    """
    Rename all episodes in the current season directory, interactively based on user preferences.
    """
    path = Path(sys.argv[1] if len(sys.argv) == 2 else os.getcwd())
    logger.info(f'Starting episode rename for path: {path}')
    if len(sys.argv) == 1:
        logger.debug('To use a different path than the current one, give it as a parameter')

    files_list = sorted(os.listdir(path))
    logger.info('Original files list ({}):\n{}'.format(len(files_list), '\n'.join(files_list)))

    guessed_show_name = path.parent.name
    show_name = input(f'Please enter the show\'s name [{guessed_show_name}]: ') or guessed_show_name
    guessed_season = path.name.rsplit(' ')[1]
    season = int(input(f'Please enter the season number [{guessed_season}]: ') or guessed_season)
    numbers_before_episode = int(input(
        'Please enter the amount of numeric characters before the episode number [0]: ') or 0)

    new_paths = []
    for file_name in files_list:
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path):
            continue
        episode_index = 0
        while not file_name[episode_index].isnumeric() or numbers_before_episode:
            if file_name[episode_index].isnumeric():
                numbers_before_episode -= 1
        episode_index += 1
        episode = int(file_name[episode_index:episode_index + 2])
        extension = file_name.split('.', 1)[1]
        new_name = f'{show_name} - S{season:02}E{episode:02}.{extension}'
        new_paths.append((full_path, os.path.join(path, new_name)))

    logger.info('New files list ({}):\n{}'.format(len(new_paths), '\n'.join([p[1] for p in new_paths])))
    should_rename = (input('Please approve this rename [y]: ') or 'y') == 'y'

    if should_rename:
        logger.info(f'Renaming {len(new_paths)} files...')
        for old_path, new_path in new_paths:
            os.rename(old_path, new_path)
    else:
        logger.info('Skipped renaming.')

    logger.info('All done!')


if __name__ == '__main__':
    main()
