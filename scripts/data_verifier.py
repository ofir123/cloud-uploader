#!/usr/local/bin/python3
import os
import sys

import logbook

# Directories settings.
MEDIA_ROOT_PATH = '/home/rclone/gdrive_decrypted'
LOG_FILE_PATH = '/var/log/data_verifier.log'

SUBTITLES_EXTENSIONS = ['.srt']

logger = logbook.Logger(__name__)


def _get_log_handlers():
    """
    Initializes all relevant log handlers.

    :return: A list of log handlers.
    """
    return [
        logbook.NullHandler(),
        logbook.StreamHandler(sys.stdout, level=logbook.INFO, bubble=True),
        logbook.RotatingFileHandler(LOG_FILE_PATH, level=logbook.DEBUG, max_size=5 * 1024 * 1024, backup_count=1,
                                    bubble=True)
    ]


def verify_dir(root, dirs, files):
    """
    Check dir doesn't contain unexpected files or sub-directories.
    
    :param root: The root dir. 
    :param dirs: The sub-directories.
    :param files: The files.
    """
    root_parent = os.path.dirname(root)
    # A TV season directory.
    if root.startswith('Season '):
        expect_dirs = False
        expect_files = True
        is_movie = False
    # A TV show directory.
    elif root_parent == 'TV':
        expect_dirs = True
        expect_files = False
        is_movie = False
    # A movie directory.
    elif root_parent == 'Movies':
        expect_dirs = False
        expect_files = True
        is_movie = True
    # General TV or Movies directory.
    elif root in ['TV', 'Movies']:
        expect_dirs = True
        expect_files = False
        is_movie = root == 'Movies'


def main():
    """
    Go over the entire media collection, and check for weird files.
    """
    with logbook.NestedSetup(_get_log_handlers()).applicationbound():
        logger.info('Data verifier started!')
        # Verify root path.
        if not os.path.isdir(MEDIA_ROOT_PATH):
            raise FileNotFoundError('Couldn\'t find media root directory! Stopping...')

        for root, dirs, files in os.walk(MEDIA_ROOT_PATH):
            logger.info('Handling dir: {}'.format(root))
            verify_root(root, dirs, files)
            for f in files:
                # Get file details.
                full_path = os.path.join(root, f)
                file_extension = os.path.splitext(f)[1]
                is_subtitle = file_extension in SUBTITLES_EXTENSIONS
                file_size = os.path.getsize(full_path)


if __name__ == '__main__':
    main()
