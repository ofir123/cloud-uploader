#!/usr/local/bin/python3
import subprocess
import sys
import os
import time

import logbook

LOG_FILE_PATH = '/var/log/gdrive_migration.log'

ACD_PREFIX = '/amazon/Amazon Cloud Drive/'
GDRIVE_PREFIX = '/gdrive'

ODRIVE_CMD = '/usr/bin/python /opt/odrive/odrive.py'
RCLONE_CMD = '/usr/bin/rclone'

logger = logbook.Logger('GDriveMigration')


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


def handle_file(input_path):
    """
    Migrate file content (if not already migrated).
    
    :param input_path: The dir path to migrate.
    :raises subprocess.CalledProcessError: If anything went wrong with one of the external processes.
    """
    logger.info('Handling file: {}'.format(input_path))
    # Check if file was already migrated.
    final_path = os.path.join(GDRIVE_PREFIX, input_path.rsplit('.cloud')[0].split(ACD_PREFIX)[1])
    if os.path.isfile(final_path):
        logger.info('File already exists: {}'.format(input_path))
        return
    is_synced = False
    # Sync with ODrive first, if needed. This phase has to work, so we try indefinitely.
    if input_path.endswith('.cloud'):
        while not is_synced:
            logger.debug('Syncing file: {}'.format(input_path))
            try:
                subprocess.check_call('{} sync "{}"'.format(ODRIVE_CMD, input_path), shell=True)
                input_path = input_path.rsplit('.cloud')[0]
                is_synced = True
            except subprocess.CalledProcessError:
                logger.error('Sync failed! Waiting for 3 seconds and trying again...')
                time.sleep(3)
    if not os.path.isfile(input_path):
        raise IOError('File not found: {}'.format(input_path))
    # Migrate with rclone!
    logger.debug('Copying file: {}'.format(input_path))
    gdrive_path = input_path.split(ACD_PREFIX)[1]
    try:
        subprocess.check_call('{} copyto "{}" "GDrive:{}"'.format(RCLONE_CMD, input_path, gdrive_path), shell=True)
    except subprocess.CalledProcessError:
        logger.error('GDrive copy failed. Deleting leftovers...')
        if os.path.isfile(final_path):
            os.remove(final_path)
        elif os.path.isdir(final_path):
            os.rmdir(final_path)
        # Still raising to enable retry.
        raise
    finally:
        # Don't forget to unsync to save storage.
        if is_synced:
            logger.debug('Unsyncing file: {}'.format(input_path))
            subprocess.check_call('{} unsync "{}"'.format(ODRIVE_CMD, input_path), shell=True)


def handle_dir(input_path):
    """
    Migrate all dir content (recursively).
    :param input_path: The dir path to migrate.
    """
    for root, _, files in os.walk(input_path):
        logger.info('Handling dir: {}'.format(root))
        for f in files:
            file_path = os.path.join(root, f)
            is_synced = False
            while not is_synced:
                try:
                    handle_file(file_path)
                    is_synced = True
                except (IOError, subprocess.CalledProcessError):
                    logger.error('Something went wrong with file: {}'.format(file_path))
                    logger.info('Waiting for 3 seconds and retrying file: {}'.format(file_path))
                    time.sleep(3)


def main():
    """
    Move the given input path (file or directory) from ODrive ACD to rclone GDrive.
    """
    with logbook.NestedSetup(_get_log_handlers()).applicationbound():
        # Parse input arguments.
        if len(sys.argv) == 2:
            input_path = os.path.abspath(sys.argv[1])
            if os.path.isfile(input_path):
                handle_file(input_path)
            elif os.path.isdir(input_path):
                handle_dir(input_path)
            else:
                print('Invalid input path given. Stopping!')
        else:
            print('Usage: python3 gdrive_migration.py <INPUT_PATH>')


if __name__ == '__main__':
    main()
