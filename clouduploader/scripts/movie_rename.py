#!/usr/local/bin/python3
import os
from pathlib import Path
import sys

import logbook

PREVIEW_LINES_NUM = 150

logger = logbook.Logger(__name__)
logbook.StreamHandler(
    sys.stdout, level=logbook.DEBUG, bubble=True,
    format_string='[{record.time:%Y-%m-%d %H:%M:%S}] {record.level_name}: {record.message}').push_application()


def main():
    """
    Rename movie in the given (or current) directory, interactively based on user preferences.
    """
    path = Path(sys.argv[1] if len(sys.argv) == 2 else os.getcwd())
    logger.info(f'Starting movie rename for path: {path}')
    if len(sys.argv) == 1:
        logger.debug('To use a different path than the current one, give it as a parameter')

    files_list = sorted(os.listdir(path))
    logger.info('Original files list ({}):\n{}'.format(len(files_list), '\n'.join(files_list)))

    guessed_movie_name = path.name
    movie_name = input(f'Please enter the movie\'s name [{guessed_movie_name}]: ') or guessed_movie_name
    dots_in_name = movie_name.count('.')

    # Perform first scan for directory details.
    should_rename_english_subtitles = False
    hebrew_subtitles_path = None
    # Main video file is determined by the file with the biggest size.
    main_video_size = 0
    main_video_path = None

    for file_name in files_list:
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path):
            continue

        file_size = os.path.getsize(full_path)
        if file_size > main_video_size:
            main_video_size = file_size
            main_video_path = full_path
        if file_name.endswith('en.srt'):
            preview = None
            try:
                preview = '\n'.join(open(full_path, 'r').readlines(PREVIEW_LINES_NUM))
            except UnicodeDecodeError:
                try:
                    preview = '\n'.join(open(full_path, 'r', encoding='cp1255').readlines(PREVIEW_LINES_NUM))
                except UnicodeDecodeError:
                    logger.error('Could\'nt find out the right encoding for the file')
            if preview:
                logger.info(f'Preview for {file_name}:\n{preview}')
            should_rename_english_subtitles = (input('Rename to Hebrew subtitles [n]: ') or 'n') == 'y'
        if file_name.endswith('he.srt'):
            hebrew_subtitles_path = full_path

    if should_rename_english_subtitles and hebrew_subtitles_path:
        logger.info(f'Deleting previous Hebrew subtitles: {hebrew_subtitles_path}')
        os.remove(hebrew_subtitles_path)

    # Files list needs to be updated because changes were made.
    files_list = sorted(os.listdir(path))
    for file_name in files_list:
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path):
            continue

        extension = file_name.split('.', dots_in_name + 1)[dots_in_name + 1]
        if should_rename_english_subtitles and extension == 'en.srt':
            extension = 'he.srt'
        new_name = f'{movie_name}.{extension}'

        if extension not in ['he.srt', 'en.srt'] and full_path != main_video_path:
            logger.info(f'Unknown file: {file_name}')
            should_delete = (input('Should delete? [y]: ') or 'y') == 'y'
            if should_delete:
                os.remove(full_path)
                logger.info('Deleted file.')
                continue

        if file_name != new_name:
            logger.info(f'Renaming {file_name} to {new_name}')
            should_rename = (input('Please approve this rename [y]: ') or 'y') == 'y'
            if should_rename:
                os.rename(full_path, os.path.join(path, new_name))
            else:
                logger.info('Skipped renaming.')

    # Change directory name as well.
    if movie_name != path.name:
        new_name = path.parent.joinpath(movie_name)
        logger.info(f'Renaming directory {path} to {new_name}')
        should_rename = (input('Please approve this rename [y]: ') or 'y') == 'y'
        if should_rename:
            os.rename(path, new_name)
        else:
            logger.info('Skipped renaming.')

    logger.info('All done!')


if __name__ == '__main__':
    main()
