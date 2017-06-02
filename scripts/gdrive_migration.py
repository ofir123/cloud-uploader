#!/usr/local/bin/python3
import subprocess
import sys
import os

import logbook

LOG_FILE_PATH = '/var/log/gdrive_migration.log'
ERRORS_LIST_PATH = '/var/log/gdrive_migration_errors.log'

ACD_PREFIX = '/amazon/Amazon Cloud Drive/'

MAX_TRIES = 3

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
    Migrate file content.
    
    :param input_path: The dir path to migrate.
    :raises subprocess.CalledProcessError: If anything went wrong with one of the external processes.
    """
    logger.info('Handling file: {}'.format(input_path))
    is_synced = False
    # Sync with ODrive first, if needed.
    if input_path.endswith('.cloud'):
        logger.debug('Syncing file: {}'.format(input_path))
        subprocess.check_call('{} sync "{}"'.format(ODRIVE_CMD, input_path), shell=True)
        input_path = input_path.rsplit('.cloud')[0]
        is_synced = True
    # Migrate with rclone!
    logger.debug('Copying file: {}'.format(input_path))
    gdrive_path = input_path.split(ACD_PREFIX)[1]
    try:
        subprocess.check_call('{} copyto "{}" "GDrive:{}"'.format(RCLONE_CMD, input_path, gdrive_path), shell=True)
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
            tries = 0
            is_failed = True
            while tries < MAX_TRIES and is_failed:
                if tries > 0:
                    logger.info('Retrying file: {}'.format(file_path))
                try:
                    handle_file(file_path)
                    is_failed = False
                except subprocess.CalledProcessError:
                    tries += 1
                    logger.error('Something went wrong with file: {}'.format(file_path))
            if is_failed:
                logger.error('Max retries! Giving up on file: {}'.format(file_path))
                open(ERRORS_LIST_PATH, 'w').write(file_path + '\n')


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
