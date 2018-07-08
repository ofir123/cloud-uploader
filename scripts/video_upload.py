#!/usr/local/bin/python3
import os
import shutil
import subprocess
import sys
import string
import random

import logbook

from clouduploader import config

logger = logbook.Logger('VideoUploader')


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
        logger.info('{} environment variable is not defined. Defining: {}'.format(
            config.ENCFS_ENVIRONMENT_VARIABLE, config.ENCFS_CONFIG_PATH))
        os.environ[config.ENCFS_ENVIRONMENT_VARIABLE] = config.ENCFS_CONFIG_PATH
    # Encrypt!
    os.makedirs(encrypted_dir)
    return_code = subprocess.call('echo {} | {} -S "{}" "{}"'.format(
        config.ENCFS_PASSWORD, config.ENCFS_PATH, encrypted_dir, plain_dir), shell=True)
    if return_code != 0:
        logger.error('Bad return code ({}) for encryption. Stopping!'.format(return_code))
        return False
    return True


def upload_video(file_path):
    """
    Upload the given file to the Google Drive videos directory.

    :param: file_path: The file to upload.
    """
    logger.info('Uploading video: {}'.format(file_path))
    file_name = os.path.basename(file_path)
    logger.info('Cloud path: {}/{}'.format(config.CLOUD_VIDEOS_PATH, file_name))
    # Create a temporary random cloud dir structure.
    original_dir = os.path.dirname(file_path)
    random_dir_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    base_dir = os.path.join(original_dir, random_dir_name)
    plain_base_dir = os.path.join(base_dir, config.CLOUD_PLAIN_PATH)
    os.makedirs(plain_base_dir)
    cloud_temp_path = os.path.join(plain_base_dir, config.CLOUD_VIDEOS_PATH)
    final_file_path = os.path.join(cloud_temp_path, file_name)
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
    gdrive_dir = upload_base_dir.split(base_dir)[1].strip('/')
    logger.info('Moving file to temporary path: {}'.format(cloud_temp_path))
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
        return_code = subprocess.call('{} --config {} copyto "{}" "GDrive:{}"'.format(
            config.RCLONE_PATH, config.RCLONE_CONFIG_PATH, upload_base_dir, gdrive_dir), shell=True)
        # Check results.
        if return_code != 0:
            logger.error('Bad return code ({}) for file: {}'.format(return_code, file_name))
            if upload_tries < config.MAX_UPLOAD_TRIES:
                logger.info('Trying again!')
            else:
                logger.error('Max retries with no success! Skipping...')
    # If everything went smoothly, add the file name to the original names log.
    if return_code == 0:
        logger.info('Upload succeeded! Deleting original file...')
    else:
        # Reverse everything.
        logger.info('Upload failed! Reversing all changes...')
        if config.SHOULD_DELETE:
            shutil.move(final_file_path, original_dir)
            os.rename(os.path.join(original_dir, file_name), file_path)
    # Unmount ENCFS directory.
    if config.SHOULD_ENCRYPT:
        subprocess.call('{} -u "{}"'.format(config.FUSERMOUNT_PATH, plain_base_dir), shell=True)
    # Delete all temporary directories.
    shutil.rmtree(base_dir)


def main():
    """
    Upload the given file to its proper Google Drive videos directory.
    """
    # Parse input arguments.
    if len(sys.argv) == 2:
        file_path = os.path.abspath(sys.argv[1])
        if os.path.isfile(file_path):
            with logbook.NestedSetup(_get_log_handlers()).applicationbound():
                upload_video(file_path)
        else:
            print('Invalid file path given. Stopping!')
    else:
        print('Usage: python3 uploader.py <FILE_PATH>')


if __name__ == '__main__':
    main()
