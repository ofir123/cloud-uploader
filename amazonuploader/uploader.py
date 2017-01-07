#!/usr/local/bin/python3.5
import os
import shutil
import subprocess
import sys
import string
import posixpath
import random

import logbook
from guessit import guessit

from amazonuploader import config

DEFAULT_VIDEO_EXTENSION = '.mkv'
DEFAULT_LANGUAGE_EXTENSION = '.en'
SUBTITLES_EXTENSIONS = ['.srt']
LANGUAGE_EXTENSIONS = ['.he', '.en']

EXTENSIONS_WHITE_LIST = ['.srt', '.mkv', '.avi', '.mp4', '.mov', '.m4v', '.wmv']
NAMES_BLACK_LIST = ['sample']

logger = logbook.Logger('AmazonUploader')


def _get_log_handlers():
    """
    Initializes all relevant log handlers.

    :return: A list of log handlers.
    """
    return [
        logbook.NullHandler(),
        logbook.StreamHandler(sys.stdout, level=logbook.DEBUG, bubble=True),
        logbook.RotatingFileHandler(config.LOGFILE, level=logbook.DEBUG, max_size=5 * 1024 * 1024, bubble=True)
    ]


def _sync():
    """
    Perform sync action.
    """
    process = subprocess.run('{} sync'.format(config.ACD_CLI_PATH), shell=True)
    if process.returncode != 0:
        logger.error('Bad return code ({}) for sync'.format(process.returncode))
    else:
        logger.info('Sync succeeded!')


def upload_file(file_path):
    """
    Upload the given file to its proper Amazon cloud directory.

    :param: file_path: The file to upload.
    """
    logger.info('Uploading file: {}'.format(file_path))
    fixed_file_path = file_path
    file_parts = os.path.splitext(file_path)
    # Verify file name.
    if len(file_parts) != 2:
        logger.info('File has no extension! Skipping...')
        return
    file_name, file_extension = file_parts
    if file_extension not in EXTENSIONS_WHITE_LIST:
        logger.info('File extension is not in white list! Skipping...')
        return
    for black_list_word in NAMES_BLACK_LIST:
        if black_list_word in file_name.lower():
            logger.info('File name contains a black listed word ({})! Skipping...'.format(black_list_word))
            return
    language_extension = None
    is_subtitles = file_extension in SUBTITLES_EXTENSIONS
    # Fake extension for subtitles in order to help guessit.
    if is_subtitles:
        # Remove language extensions if needed.
        file_parts = os.path.splitext(file_name)
        if len(file_parts) == 2:
            fixed_file_name, language_extension = file_parts
            if language_extension in LANGUAGE_EXTENSIONS:
                fixed_file_path = fixed_file_name + DEFAULT_VIDEO_EXTENSION
            else:
                language_extension = DEFAULT_LANGUAGE_EXTENSION
                fixed_file_path = file_name + DEFAULT_VIDEO_EXTENSION
    # Create cloud path based on guessit results.
    cloud_dir = None
    cloud_file = None
    guess_results = guessit(os.path.basename(fixed_file_path))
    video_type = guess_results.get('type')
    title = guess_results.get('title')
    # Make sure every word starts with a capital letter.
    if title:
        title = title.title()
    if video_type == 'episode' and title:
        season = guess_results.get('season')
        if season:
            episode = guess_results.get('episode')
            if episode:
                cloud_dir = '{}/{}/Season {:02d}'.format(config.TV_PATH, title, season)
                cloud_file = '{} - S{:02d}E{:02d}'.format(title, season, episode)
    elif video_type == 'movie' and title:
        year = guess_results.get('year')
        if year:
            cloud_dir = '{}/{} ({})'.format(config.MOVIE_PATH, title, year)
            cloud_file = '{} ({})'.format(title, year)
    if cloud_dir and cloud_file:
        if language_extension:
            cloud_file += language_extension
        cloud_file += file_extension
        logger.info('Cloud path: {}'.format(posixpath.join(cloud_dir, cloud_file)))
        # Create a temporary random cloud dir structure.
        random_dir_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        base_dir = os.path.join(os.path.dirname(file_path), random_dir_name)
        plain_base_dir = os.path.join(base_dir, 'plain')
        cloud_temp_path = os.path.join(plain_base_dir, cloud_dir)
        os.makedirs(cloud_temp_path, exist_ok=True)
        cloud_temp_path = os.path.join(cloud_temp_path, cloud_file)
        shutil.move(file_path, cloud_temp_path)
        # Encrypt if needed.
        if config.SHOULD_ENCRYPT:
            logger.info('Encrypting directory tree...')
            # Verify config environment variable first.
            if not os.environ.get(config.ENCFS_ENVIRONMENT_VARIABLE):
                logger.error('{} environment variable is not defined. Stopping!'.format(
                    config.ENCFS_ENVIRONMENT_VARIABLE))
                # Reverse move action, delete directories and stop.
                shutil.move(cloud_temp_path, file_path)
                shutil.rmtree(base_dir)
                return
            # Encrypt!
            encryption_base_dir = os.path.join(base_dir, 'encrypted')
            os.makedirs(encryption_base_dir)
            encryption_process = subprocess.run('{} "{}" "{}"'.format(
                config.ENCFS_PATH, encryption_base_dir, plain_base_dir), shell=True)
            encryption_return_code = encryption_process.returncode
            if encryption_return_code != 1:
                logger.error('Bad return code ({}) for encryption of file: {}. Stopping!'.format(
                    encryption_return_code, cloud_file))
                # Reverse move action, delete directories and stop.
                shutil.move(cloud_temp_path, file_path)
                shutil.rmtree(base_dir)
                return
            # Upload the encrypted directory tree instead of the plain one.
            upload_base_dir = encryption_base_dir
        else:
            upload_base_dir = plain_base_dir
        # Sync first.
        _sync()
        # Upload!
        upload_tries = 0
        return_code = 1
        while return_code != 0 and upload_tries < config.MAX_UPLOAD_TRIES:
            logger.info('Uploading file...')
            upload_tries += 1
            process = subprocess.run('{} upload -o --remove-source-files "{}/*" /'.format(
                config.ACD_CLI_PATH, upload_base_dir), shell=True)
            # Check results.
            return_code = process.returncode
            if return_code != 0:
                logger.error('Bad return code ({}) for file: {}'.format(process.returncode, cloud_file))
                if upload_tries < config.MAX_UPLOAD_TRIES:
                    logger.info('Trying again!')
                    # Sync in case the file was actually uploaded.
                    _sync()
                else:
                    logger.error('Max retries with no success! Skipping...')
        # If everything went smoothly, add the file name to the original names log.
        if return_code == 0:
            logger.info('Upload succeeded! Deleting original file...')
            # Unmount ENCFS directory tree first.
            if config.SHOULD_ENCRYPT:
                subprocess.run('{} -u "{}"'.format(config.FUSERMOUNT_PATH, plain_base_dir), shell=True)
            shutil.rmtree(base_dir)
            if not is_subtitles:
                open(config.ORIGINAL_NAMES_LOG, 'a', encoding='UTF-8').write(file_path + '\n')
    else:
        logger.info('Couldn\'t guess file info. Skipping...')


def main():
    """
    Upload the given file to its proper Amazon cloud directory.
    """
    # Parse input arguments.
    if len(sys.argv) == 2:
        file_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(file_path):
            with logbook.NestedSetup(_get_log_handlers()).applicationbound():
                upload_file(file_path)
        else:
            print('Invalid file path given. Stopping!')
    else:
        print('Usage: python3.5 uploader.py <FILE_PATH>')


if __name__ == '__main__':
    main()
