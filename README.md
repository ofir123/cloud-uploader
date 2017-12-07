cloud-uploader
===============

A python script for automatic upload to Google Drive.

The script guesses the proper directory structure for a given file and uploads it using rclone.

Usage
=====

First of all, install the shows-formatter package (from my GitHub repository).

Then, Install the script as follows:

	$ python setup.py develop

Edit the configuration with your settings:

	$ vim config.py

That's it.

The script can be used from the command line:

	$ clouduploader /download/The.Wire.S01E01.HDTV
