#!/usr/local/bin/python3
import os
import random
import shutil
import string
import subprocess
import sys

from guessit import guessit
import logbook
from showsformatter import format_show

from clouduploader import config

DEFAULT_VIDEO_EXTENSION = '.mkv'
DEFAULT_LANGUAGE_EXTENSION = '.en'
SUBTITLES_EXTENSIONS = ['.srt']
LANGUAGE_EXTENSIONS = ['.he', '.en']

EXTENSIONS_WHITE_LIST = ['.srt', '.mkv', '.avi', '.mp4', '.m4v', '.wmv', '.mpg']
NAMES_BLACK_LIST = ['sample']

logger = logbook.Logger('CloudUploader')


def _get_log_handlers():
    """
    Initializes all relevant log handlers.

    :return: A list of log handlers.
    """
    return [
        logbook.StreamHandler(sys.stdout, level=logbook.DEBUG, bubble=True),
        logbook.RotatingFileHandler(config.LOGFILE, level=logbook.DEBUG, max_size=5 * 1024 * 1024, backup_count=1,
                                    bubble=True)
    ]


def _encrypt(encrypted_dir, plain_dir):
    """
    Encrypt the given plain directory.

    :param encrypted_dir: The encrypted directory to create.
    :param plain_dir: The plain directory to encrypt (recursively).
    :return: True if succeeded, and False otherwise.
    """
    logger.info('Encrypting directory tree...')

    # Verify config environment variable first.
    if not os.environ.get(config.ENCFS_ENVIRONMENT_VARIABLE):
        logger.info(f'{config.ENCFS_ENVIRONMENT_VARIABLE} environment variable is not defined. '
                    f'Defining: {config.ENCFS_CONFIG_PATH}')
        os.environ[config.ENCFS_ENVIRONMENT_VARIABLE] = config.ENCFS_CONFIG_PATH

    # Encrypt!
    os.makedirs(encrypted_dir)
    return_code = subprocess.call(
        f'echo {config.ENCFS_PASSWORD} | {config.ENCFS_PATH} -S "{encrypted_dir}" "{plain_dir}"', shell=True)

    if return_code != 0:
        logger.error(f'Bad return code ({return_code}) for encryption. Stopping!')
        return False

    return True


def _extract_ufc_path(file_name):
    """
    Extract UFC cloud dir and cloud file name from the given file name.

    :param file_name: The file name to extract data from.
    :return: A tuple of format (cloud_dir, cloud_file)
    """
    guess_results = guessit(file_name)

    # Get real episode number.
    episode_num = guess_results.get('episode')
    if not episode_num:
        return None, None
    season = guess_results.get('season')
    if season:
        episode_num += 100 * season
    episode_num = '{:03}'.format(episode_num)

    # Get title.
    lowercase_file_name = file_name.lower()
    if 'fox' in lowercase_file_name:
        title = 'UFC On FOX'
    elif 'espn' in lowercase_file_name:
        title = 'UFC On ESPN'
    elif 'fight' in lowercase_file_name and 'night' in lowercase_file_name or 'fn' in lowercase_file_name:
        title = 'UFC Fight Night'
    else:
        title = 'UFC'

    cloud_dir = os.path.join(config.CLOUD_UFC_PATH, f'{title} {episode_num}')
    cloud_file = f'{title} {episode_num}'
    if 'prelim' in lowercase_file_name:
        cloud_file += ' - Preliminaries'
    return cloud_dir, cloud_file


def _extract_masterclass_path(file_name):
    """
    Extract Masterclass cloud dir and cloud file name from the given file name.

    :param file_name: The file name to extract data from.
    :return: A tuple of format (cloud_dir, cloud_file)
    """
    cloud_dir = config.CLOUD_VIDEOS_PATH
    cloud_file = os.path.splitext(file_name)[0]
    return cloud_dir, cloud_file


def guess_path(file_name):
    """
    Guess cloud dir and cloud file name from the given file name.

    :param file_name: The file name to guess on.
    :return: A tuple of format (cloud_dir, cloud_file)
    """
    cloud_dir = None
    cloud_file = None

    # Start guessing!
    guess_results = guessit(file_name)
    video_type = guess_results.get('type')
    title = guess_results.get('title')

    if isinstance(title, list):
        title = title[0]

    if video_type == 'episode' and title:
        # Translate show title if needed.
        title = format_show(title)
        season = guess_results.get('season')

        # Skip rare cases of weird episodes names.
        if season and not isinstance(season, list):
            episode = guess_results.get('episode')

            if episode:
                # Dirs that end with . are evil!
                fixed_dir_name = title.rstrip('.')
                cloud_dir = os.path.join(config.CLOUD_TV_PATH, fixed_dir_name, 'Season {:02d}'.format(season))

                if isinstance(episode, list):
                    episode_str = 'E{:02d}-E{:02d}'.format(episode[0], episode[-1])
                else:
                    episode_str = 'E{:02d}'.format(episode)
                cloud_file = '{} - S{:02d}{}'.format(title, season, episode_str)

    elif video_type == 'movie' and title:
        # Make sure every word starts with a capital letter.
        title = title.title()
        year = guess_results.get('year')

        if year:
            cloud_dir = os.path.join(config.CLOUD_MOVIES_PATH, f'{title} ({year})')
            cloud_file = f'{title} ({year})'

    return cloud_dir, cloud_file


def upload_file(file_path):
    """
    Upload the given file to its proper Google Drive cloud directory.

    :param: file_path: The file to upload.
    """
    logger.info(f'Uploading file: {file_path}')
    fixed_file_path = file_path
    file_parts = os.path.splitext(file_path)

    # Verify file name.
    if len(file_parts) != 2:
        logger.info('File has no extension! Skipping...')
        return
    file_name, file_extension = file_parts
    file_extension = file_extension.lower()
    if file_extension not in EXTENSIONS_WHITE_LIST:
        logger.info('File extension is not in white list! Skipping...')
        return
    for black_list_word in NAMES_BLACK_LIST:
        if black_list_word in file_name.lower():
            logger.info(f'File name contains a black listed word ({black_list_word})! Skipping...')
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

    fixed_file_name = os.path.basename(fixed_file_path)
    # Remove brackets group name prefix.
    if fixed_file_name.startswith('[') and ']' in fixed_file_name:
        fixed_file_name = fixed_file_name.split(']', 1)[1]

    # Check if dubbed.
    is_kids = 'hebdub' in fixed_file_name.lower() or 'hebdub' in fixed_file_path.lower() or \
        'hebrew.dubbed' in fixed_file_name.lower() or 'hebrew.dubbed' in fixed_file_path.lower() or \
        'hebrew dubbed' in fixed_file_name.lower() or 'hebrew dubbed' in fixed_file_path.lower()

    if 'ufc' in fixed_file_name.lower() or 'ufc' in fixed_file_path.lower():
        cloud_dir, cloud_file = _extract_ufc_path(fixed_file_name)
    elif 'masterclass' in fixed_file_name.lower() or 'masterclass' in fixed_file_path.lower():
        cloud_dir, cloud_file = _extract_masterclass_path(fixed_file_name)
    else:
        cloud_dir, cloud_file = guess_path(fixed_file_name)

    if cloud_dir and cloud_file:
        if is_kids:
            cloud_dir = cloud_dir.replace(config.CLOUD_MOVIES_PATH, config.CLOUD_KIDS_MOVIES_PATH, 1).replace(config.CLOUD_TV_PATH, config.CLOUD_KIDS_TV_PATH, 1)
            cloud_file += ' - Hebrew'
        if language_extension:
            cloud_file += language_extension

        cloud_file += file_extension
        logger.info('Cloud path: {}'.format(os.path.join(cloud_dir, cloud_file)))
        # Create a temporary random cloud dir structure.
        original_dir = os.path.dirname(file_path)
        random_dir_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        base_dir = os.path.join(original_dir, random_dir_name)
        plain_base_dir = os.path.join(base_dir, config.CLOUD_PLAIN_PATH)
        os.makedirs(plain_base_dir)
        cloud_temp_path = os.path.join(plain_base_dir, cloud_dir)
        final_file_path = os.path.join(cloud_temp_path, cloud_file)
        # Use the plain directory when uploading, unless encryption is enabled.
        upload_base_dir = plain_base_dir
        # Set up encryption if needed.
        if config.SHOULD_ENCRYPT:
            encrypted_base_dir = os.path.join(base_dir, config.CLOUD_ENCRYPTED_PATH)
            encryption_successful = _encrypt(encrypted_base_dir, plain_base_dir)
            if not encryption_successful:
                # Delete directories and stop.
                shutil.rmtree(base_dir)
                return
            # Upload the encrypted directory tree instead of the plain one.
            upload_base_dir = encrypted_base_dir
        gdrive_dir = upload_base_dir.split(base_dir)[1].strip(os.path.sep)
        logger.info(f'Moving file to temporary path: {cloud_temp_path}')
        os.makedirs(cloud_temp_path)
        if config.SHOULD_DELETE:
            shutil.move(file_path, cloud_temp_path)
        else:
            shutil.copy(file_path, cloud_temp_path)
        os.rename(os.path.join(cloud_temp_path, os.path.basename(file_path)), final_file_path)

        # Upload!
        upload_tries = 0
        return_code = 1
        while return_code != 0 and upload_tries < config.MAX_UPLOAD_TRIES:
            logger.info('Uploading file...')
            upload_tries += 1
            process_result = subprocess.run(
                f'{config.RCLONE_PATH} --config {config.RCLONE_CONFIG_PATH} copyto --update "{upload_base_dir}" '
                f'"GDrive:{gdrive_dir}"', shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                check=False)
            # Check results.
            return_code = process_result.returncode
            if return_code != 0:
                logger.error(
                    f'Bad return code ({return_code}) for file: {cloud_file}. Output:\n{process_result.stdout}')
                if upload_tries < config.MAX_UPLOAD_TRIES:
                    logger.info('Trying again!')
                else:
                    logger.error('Max retries with no success! Skipping...')
        # If everything went smoothly, add the file name to the original names log.
        if return_code == 0:
            logger.info('Upload succeeded! Deleting original file...')
            if not is_subtitles:
                open(config.ORIGINAL_NAMES_LOG, 'a', encoding='UTF-8').write(file_path + '\n')
        else:
            # Reverse everything.
            logger.info('Upload failed! Reversing all changes...')
            if config.SHOULD_DELETE:
                shutil.move(final_file_path, original_dir)
                os.rename(os.path.join(original_dir, cloud_file), file_path)
        # Unmount ENCFS directory.
        if config.SHOULD_ENCRYPT:
            subprocess.call(f'{config.FUSERMOUNT_PATH} -u "{plain_base_dir}"', shell=True)
        # Delete all temporary directories.
        shutil.rmtree(base_dir)
    else:
        logger.info('Couldn\'t guess file info. Skipping...')


def main():
    """
    Upload the given file to its proper Google Drive cloud directory.
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
        print('Usage: python3 uploader.py <FILE_PATH>')


if __name__ == '__main__':
    main()
