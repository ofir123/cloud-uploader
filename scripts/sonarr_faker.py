#!/usr/local/bin/python3
import os
import sys
import shutil
from pathlib import Path

import logbook

# Directories settings.
TV_ROOT_PATH = '/mnt/vdb/plexdrive/gdrive_decrypted/TV'
FAKE_ROOT_PATH = '/mnt/vdb/fake/TV'
LOG_FILE_PATH = '/var/log/sonarr_faker.log'

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


def main():
    """
    Go over the entire TV collection, and create fake files in a writable directory, so Sonarr would scan them.
    """
    with logbook.NestedSetup(_get_log_handlers()).applicationbound():
        logger.info('Sonarr faker started!')
        # Verify root path.
        if not os.path.isdir(TV_ROOT_PATH):
            raise FileNotFoundError('Couldn\'t find TV root directory! Stopping...')
        # Delete previous fake directory.
        if os.path.isdir(FAKE_ROOT_PATH):
            shutil.rmtree(FAKE_ROOT_PATH)
        # Start working!
        for root, dirs, files in os.walk(TV_ROOT_PATH):
            logger.info('Handling dir: {}'.format(root))
            # Create a fake directory.
            fake_root = root.replace(TV_ROOT_PATH, FAKE_ROOT_PATH)
            os.makedirs(fake_root, exist_ok=True)
            for f in files:
                # Create a fake file.
                fake_path = os.path.join(fake_root, f)
                Path(fake_path).touch()
        logger.info('All done!')


if __name__ == '__main__':
    main()
