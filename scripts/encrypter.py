import os
import shelve
import shutil
import subprocess

SHELVE_PATH = '/mnt/vdb/shelve'

AMAZON_DIR = '/mnt/vdb/amazon'
AMAZON_MEDIA_DIR = os.path.join(AMAZON_DIR, 'Media')
CURRENT_AMAZON_DIR = 'TV'

TEMP_PLAIN_DIR = '/mnt/vdb/tmp/Media'
TEMP_ENCRYPTED_DIR = '/mnt/vdb/tmp/Encrypted'

ACD_CLI_PATH = '/usr/bin/acd_cli'
ENCFS_PATH = '/usr/bin/encfs'
FUSERMOUNT_PATH = '/usr/bin/fusermount'
ENCFS_PASSWORD = 'Password1'

MAX_TRIES = 3


def main():
    """
    Downloads all media from the Amazon cloud drive, and uploads it back encrypted.
    """
    # Sync before starting anything...
    subprocess.call('{} sync'.format(ACD_CLI_PATH), shell=True)
    files_map = shelve.open(SHELVE_PATH)
    try:
        for root, _, files in os.walk(os.path.join(AMAZON_MEDIA_DIR, CURRENT_AMAZON_DIR)):
            for f in files:
                file_path = os.path.join(root, f)
                # Skip files that were encrypted in the past.
                if files_map.get(file_path):
                    print('Skipping {}...'.format(file_path))
                    continue
                print('Downloading {}...'.format(f))
                # Create encryption directory.
                os.makedirs(TEMP_PLAIN_DIR)
                os.makedirs(TEMP_ENCRYPTED_DIR)
                return_code = subprocess.call('echo {} | {} -S "{}" "{}"'.format(
                    ENCFS_PASSWORD, ENCFS_PATH, TEMP_ENCRYPTED_DIR, TEMP_PLAIN_DIR), shell=True)
                if return_code != 0:
                    print('Bad return code ({}) for encryption. Skipping file!'.format(return_code))
                    continue
                # Download!
                new_file_path = file_path.replace(AMAZON_MEDIA_DIR, TEMP_PLAIN_DIR)
                new_base_dir = os.path.dirname(new_file_path)
                os.makedirs(new_base_dir)
                cloud_path = file_path.replace(AMAZON_DIR, '')
                tries = 0
                return_code = 1
                while return_code != 0 and tries < MAX_TRIES:
                    tries += 1
                    return_code = subprocess.call('{} download "{}" "{}"'.format(
                        ACD_CLI_PATH, cloud_path, new_base_dir), shell=True)
                    # Check results.
                    if return_code != 0:
                        print('Bad return code ({}) for file: {}'.format(return_code, os.path.basename(cloud_path)))
                        if tries < MAX_TRIES:
                            print('Trying again!')
                        else:
                            print('Max retries with no success! Skipping...')
                # Upload!
                print('Uploading {}...'.format(f))
                tries = 0
                return_code = 1
                while return_code != 0 and tries < MAX_TRIES:
                    tries += 1
                    return_code = subprocess.call('{} upload "{}" /'.format(
                        ACD_CLI_PATH, TEMP_ENCRYPTED_DIR), shell=True)
                    # Check results.
                    if return_code != 0:
                        print('Bad return code ({}) for file: {}'.format(return_code, os.path.basename(new_file_path)))
                        if tries < MAX_TRIES:
                            print('Trying again!')
                            # Sync in case the file was actually uploaded.
                            subprocess.call('{} sync'.format(ACD_CLI_PATH), shell=True)
                        else:
                            print('Max retries with no success! Skipping...')
                # If everything went smoothly, add the file path to the persistent shelve.
                if return_code == 0:
                    files_map[file_path] = True
                    print('Done!')
                else:
                    files_map[file_path] = False
                    print('Upload failed!')
                subprocess.call('{} -u "{}"'.format(FUSERMOUNT_PATH, TEMP_PLAIN_DIR), shell=True)
                # Delete all temporary directories.
                shutil.rmtree(TEMP_PLAIN_DIR)
                shutil.rmtree(TEMP_ENCRYPTED_DIR)
                # Reset sync.
                subprocess.call('{} sync'.format(ACD_CLI_PATH), shell=True)
                if not os.path.isdir(AMAZON_DIR):
                    print('Resetting sync...')
                    subprocess.call('{} umount {}'.format(ACD_CLI_PATH, AMAZON_DIR), shell=True)
                    subprocess.call('{} sync'.format(ACD_CLI_PATH), shell=True)
                    subprocess.call('{} mount -ao {}'.format(ACD_CLI_PATH, AMAZON_DIR), shell=True)
    finally:
        files_map.close()


if __name__ == '__main__':
    main()
