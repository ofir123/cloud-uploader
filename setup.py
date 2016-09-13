from setuptools import setup, find_packages


setup(
    name='amazonuploader',
    version='1.0',
    packages=find_packages(),
    long_description=open('README.md').read(),
    install_requires=['logbook', 'guessit', 'acdcli'],
    entry_points={
      'console_scripts': [
          'amazonuploader = amazonuploader:main',
      ]
    }
)
