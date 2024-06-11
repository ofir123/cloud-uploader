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
    logger.info(f'Starting suffix add for path: {path}')
    if len(sys.argv) == 1:
        logger.debug('To use a different path than the current one, give it as a parameter')

    files_list = sorted(os.listdir(path))
    logger.info('Original files list ({}):\n{}'.format(len(files_list), '\n'.join(files_list)))

    suffix = input(f'Please enter a suffix []: ') or ''

    new_paths = []
    file_index = 0
    for file_name in tqdm(files_list):
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path):
            continue

        # Subtitle extension might contain an additional two letters extension for the language.
        if file_name.endswith('.srt') and len(file_name) > 7 and file_name[-7] == '.':
            name = file_name[:-7]
            extension = file_name[-6:]
        else:
            name = file_name.rsplit('.', 1)[0]
            extension = file_name.rsplit('.')[-1]
        new_name = f'{name} - {suffix}.{extension}'
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
