amazon-uploader
===========

A python script for automatic upload to the Amazon cloud storage.

The script guesses the proper directory structure for a given file and uploads it using acd_cli.

Usage
===========
Install the script as follows:

	$ python setup.py develop

Edit the configuration with your settings:

	$ vim config.py

That's it.

The script can be used from the command line:

	$ amazonuploader /download/The.Wire.S01E01.HDTV
