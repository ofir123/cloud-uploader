# Post-upload settings.
SHOULD_DELETE = True

# acd_cli settings.
ACD_CLI_PATH = '/usr/bin/acd_cli'
MAX_UPLOAD_TRIES = 3

# encfs settings.
SHOULD_ENCRYPT = True
ENCFS_PATH = '/usr/bin/encfs'
FUSERMOUNT_PATH = '/usr/bin/fusermount'
ENCFS_ENVIRONMENT_VARIABLE = 'ENCFS6_CONFIG'
ENCFS_CONFIG_PATH = '/mnt/vdb/encfs6.xml'
ENCFS_PASSWORD = 'Password1'

# Directories settings.
CLOUD_ENCRYPTED_PATH = 'Encrypted'
CLOUD_PLAIN_PATH = 'Media'
CLOUD_TV_PATH = 'TV'
CLOUD_MOVIE_PATH = 'Movies'
CLOUD_VIDEO_PATH = 'Videos'
ORIGINAL_NAMES_LOG = '/mnt/vdb/data/original_names.log'

# Log settings.
LOGFILE = '/var/log/amazon_uploader.log'
