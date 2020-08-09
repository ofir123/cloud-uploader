from setuptools import setup, find_packages

setup(
    name='clouduploader',
    version='1.0',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=['logbook', 'guessit', 'plexapi', 'babelfish', 'requests', 'subliminal', 'showsformatter'],
    entry_points={
        'console_scripts': [
            'clouduploader = clouduploader.uploader:main',
            'sonarr_faker = clouduploader.scripts.sonarr_faker:main',
            'subtitles_monitor = clouduploader.scripts.subtitles_monitor:main',
            'episodes_rename = clouduploader.scripts.episodes_rename:main',
            'movie_rename = clouduploader.scripts.movie_rename:main',
        ]
    }
)
