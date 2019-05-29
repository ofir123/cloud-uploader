#!/usr/local/bin/python3
import os
from pathlib import Path
import shutil
import sys

import logbook

# Directories settings.
GDRIVE_ROOT_PATH = '/mnt/vdb/plexdrive/gdrive_decrypted'
FAKE_ROOT_PATH = '/mnt/vdb/fake'
LOG_FILE_PATH = '/var/log/sonarr_faker.log'

logger = logbook.Logger(__name__)


def _get_log_handlers():
    """
    Initializes all relevant log handlers.

    :return: A list of log handlers.
    """
    return [
        logbook.StreamHandler(sys.stdout, level=logbook.INFO, bubble=True),
        logbook.RotatingFileHandler(LOG_FILE_PATH, level=logbook.DEBUG, max_size=5 * 1024 * 1024, backup_count=1,
                                    bubble=True)
    ]


def main():
    """
    Go over the entire TV collection, and create fake files in a writable directory, so Sonarr would scan them.
    """
    with logbook.NestedSetup(_get_log_handlers()).applicationbound():
        logger.info('Sonarr faker started!')
        # Verify root path.
        if not os.path.isdir(GDRIVE_ROOT_PATH):
            raise FileNotFoundError('Couldn\'t find GDrive root directory! Stopping...')

        # Delete previous fake directory.
        should_delete = len(sys.argv) == 2 and sys.argv[1] == '-d'
        if os.path.isdir(FAKE_ROOT_PATH) and should_delete:
            logger.info('Deleting previous fake directory...')
            shutil.rmtree(FAKE_ROOT_PATH)

        # Start working!
        for root, dirs, files in os.walk(GDRIVE_ROOT_PATH):
            logger.info(f'Handling dir: {root}')
            # Create a fake directory.
            fake_root = root.replace(GDRIVE_ROOT_PATH, FAKE_ROOT_PATH)
            os.makedirs(fake_root, exist_ok=True)

            for f in files:
                # Create a fake file.
                fake_path = os.path.join(fake_root, f)
                Path(fake_path).touch()

        logger.info('All done!')


if __name__ == '__main__':
    main()
