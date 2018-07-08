#!/usr/local/bin/python3
import datetime
from collections import defaultdict
import os
import sys
import time

import requests
import logbook
import babelfish
from guessit import guessit
import subliminal
from subliminal.cache import region
from subliminal.cli import dirs, cache_file, MutexLock
from subliminal.subtitle import get_subtitle_path
from plexapi.server import PlexServer

from clouduploader import config
from clouduploader.uploader import upload_file, get_file_path_details

# Ignore SSL warnings.
requests.packages.urllib3.disable_warnings()

# Directories settings.
MEDIA_ROOT_PATH = '/mnt/vdb/plexdrive/gdrive_decrypted'
TEMP_PATH = '/tmp'
# A map between each language and its favorite subliminal providers (None for all providers).
PROVIDERS_MAP = {
    babelfish.Language('heb'): ['cinemast', 'wizdom'],
    babelfish.Language('eng'): None
}
# A map between each provider and its credentials.
PROVIDER_CONFIGS = {
    'cinemast': {
        'username': 'subliminal@gmail.com',
        'password': 'subliminal'
    }
}

# The monitor will look only at the latest X files (or all of them if RESULTS_LIMIT is None).
RESULTS_LIMIT = 1000

SUBTITLES_EXTENSION = '.srt'
LANGUAGE_EXTENSIONS = ['.he', '.en']
LOG_FILE_PATH = '/var/log/subtitles_monitor.log'

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


def configure_subtitles_cache():
    """
    Configure the subliminal cache settings.
    Should be called once when the program starts.
    """
    # Configure the subliminal cache.
    cache_dir = dirs.user_cache_dir
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file_path = os.path.join(cache_dir, cache_file)
    region.configure('dogpile.cache.dbm', expiration_time=datetime.timedelta(days=30),
                     arguments={'filename': cache_file_path, 'lock_factory': MutexLock})


def refresh_plex_item(title, season=None, episodes=None):
    """
    Use the Plex API in order to refresh an item.

    :param title: The item title.
    :param season: The season number.
    :param episodes: The episode numbers list.
    """
    logger.info('Updating Plex...')
    is_episode = season is not None and episodes is not None
    for base_url, token in config.PLEX_SERVERS:
        with requests.Session() as session:
            # Ignore SSL errors.
            session.verify = False
            try:
                plex = PlexServer(base_url, token, session=session)
                if is_episode:
                    plex_season = plex.library.section('TV Shows').get(title).seasons()[season - 1].episodes()
                    for episode in episodes:
                        plex_season[episode - 1].refresh()
                else:
                    plex.library.section('Movies').get(title).refresh()
            except Exception:
                episode_details = ' - Season {} Episodes {}'.format(season, ', '.join([str(e) for e in episodes]))
                logger.exception('Failed to update item {}{}'.format(
                    title, episode_details if is_episode else ''))


def find_file_subtitles(original_path, current_path, language):
    """
    Finds subtitles for the given video file path in the given language.
    Downloaded subtitles will be saved next to the video file.

    :param original_path: The original path of the video file to find subtitles to.
    :param current_path: The current video path (to save the subtitles file next to).
    :param language: The language to search for.
    :return: The subtitles file path, or None if a problem occurred.
    """
    logger.info('Searching {} subtitles for file: {}'.format(language.alpha3, original_path))
    try:
        subtitles_result = None
        original_file_name = os.path.basename(original_path)
        # Get required video information.
        video = subliminal.Video.fromguess(current_path, guessit(original_file_name))
        # Try using providers specified by the user.
        providers = PROVIDERS_MAP.get(language)
        current_result = subliminal.download_best_subtitles(
            {video}, languages={language}, providers=providers, provider_configs=PROVIDER_CONFIGS).values()
        if current_result:
            current_result = list(current_result)[0]
            if current_result:
                subtitles_result = current_result[0]
        # Handle results.
        if not subtitles_result:
            logger.info('No subtitles were found. Moving on...')
        else:
            logger.info('Subtitles found! Saving files...')
            # Save subtitles alongside the video file (if they're not empty).
            if subtitles_result.content is None:
                logger.debug('Skipping subtitle {}: no content'.format(subtitles_result))
            else:
                subtitles_file_name = get_subtitle_path(original_file_name, subtitles_result.language)
                subtitles_path = os.path.join(TEMP_PATH, subtitles_file_name)
                logger.info('Saving {} to: {}'.format(subtitles_result, subtitles_path))
                try:
                    open(subtitles_path, 'wb').write(subtitles_result.content)
                    logger.info('Uploading {}'.format(subtitles_path))
                    try:
                        upload_file(subtitles_path)
                    except Exception:
                        # Catch all exceptions so the script won't stop.
                        logger.exception('Failed to upload file: {}'.format(subtitles_path))
                except OSError:
                    logger.error('Failed to save subtitles in path: {}'.format(subtitles_path))
                return subtitles_path
        return None
    except ValueError:
        # Subliminal raises a ValueError if the given file is not a video file.
        logger.info('Not a video file. Moving on...')
    except Exception:
        logger.exception('Error in Subliminal. Moving on...')


def main():
    """
    Start going over the video files and search for missing subtitles.
    """
    with logbook.NestedSetup(_get_log_handlers()).applicationbound():
        logger.info('Subtitles Monitor started!')
        # Verify paths.
        if not os.path.isfile(config.ORIGINAL_NAMES_LOG):
            raise FileNotFoundError('Couldn\'t read original names file! Stopping...')
        if not os.path.isdir(MEDIA_ROOT_PATH):
            raise NotADirectoryError('Couldn\'t find media root directory! Stopping...')
        try:
            original_paths_list = []
            subtitles_map = defaultdict(int)
            # Set subliminal cache first.
            logger.debug('Setting subtitles cache...')
            configure_subtitles_cache()
            logger.info('Going over the original names file...')
            with open(config.ORIGINAL_NAMES_LOG, 'r', encoding='utf8') as original_names_file:
                line = original_names_file.readline()
                while line != '':
                    original_path = line.strip()
                    original_paths_list.append(original_path)
                    if RESULTS_LIMIT and len(original_paths_list) > RESULTS_LIMIT:
                        original_paths_list.pop(0)
                    # Fetch next line.
                    line = original_names_file.readline()
            logger.info('Searching for subtitles for the {} newest videos...'.format(RESULTS_LIMIT))
            for original_path in original_paths_list:
                video_details, parent_dir, guessed_file_name = get_file_path_details(original_path)
                if not (parent_dir and guessed_file_name):
                    continue
                base_dir = os.path.join(
                    MEDIA_ROOT_PATH, config.CLOUD_TV_PATH if video_details['type'] == 'episode' else
                    config.CLOUD_MOVIES_PATH)
                current_path = os.path.join(base_dir, parent_dir,
                                            '{}{}'.format(guessed_file_name, os.path.splitext(original_path)[1]))
                # Check actual video file.
                if current_path and os.path.isfile(current_path):
                    logger.info('Checking subtitles for: {}'.format(current_path))
                    # Find missing subtitle files.
                    video_base_path = os.path.splitext(current_path)[0]
                    languages_list = []
                    for language_extension in LANGUAGE_EXTENSIONS:
                        if not os.path.isfile(video_base_path + language_extension + SUBTITLES_EXTENSION):
                            languages_list.append(babelfish.Language.fromalpha2(language_extension.lstrip('.')))
                    # Download missing subtitles.
                    for language in languages_list:
                        result_path = find_file_subtitles(original_path, current_path, language)
                        if result_path:
                            subtitles_map[language.alpha3] += 1
                            if config.PLEX_SERVERS:
                                # Refresh Plex data (after waiting some time for the file to upload).
                                time.sleep(5)
                                episode = video_details.get('episode')
                                refresh_plex_item(video_details['title'], video_details.get('season'),
                                                  [episode] if not isinstance(episode, list) else episode)
                else:
                    logger.info('Couldn\'t find: {}'.format(current_path))
            logger.info('All done! The results are: {}'.format(
                ', '.join(['{} - {}'.format(language, counter) for language, counter in subtitles_map.items()])))
        except:
            logger.exception('Critical exception occurred!')
            raise


if __name__ == '__main__':
    main()
