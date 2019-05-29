from setuptools import setup, find_packages


setup(
    name='clouduploader',
    version='1.0',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=['logbook', 'guessit', 'plexapi', 'babelfish', 'requests', 'subliminal', 'showsformatter'],
    entry_points={
      'console_scripts': [
          'clouduploader = clouduploader:main',
      ]
    }
)
