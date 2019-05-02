OpenSubtitlesDownload.py
========================

[![GitHub release](https://img.shields.io/github/release/emericg/OpenSubtitlesDownload.svg?style=flat-square)](https://github.com/emericg/OpenSubtitlesDownload/releases)
[![GitHub contributors](https://img.shields.io/github/contributors/emericg/OpenSubtitlesDownload.svg?style=flat-square)](https://github.com/emericg/OpenSubtitlesDownload/graphs/contributors)
[![GitHub issues](https://img.shields.io/github/issues/emericg/OpenSubtitlesDownload.svg?style=flat-square)](https://github.com/emericg/OpenSubtitlesDownload/issues)
[![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-brightgreen.svg?style=flat-square)](http://www.gnu.org/licenses/gpl-3.0)

Introduction
------------

**OpenSubtitlesDownload.py** is a small software written in python, built to help you **quickly find and download subtitles for your favorite videos**. It can be used as a nautilus script, or as a regular application working under GNOME or KDE desktop environments. You can also use it in full CLI mode (Command Line Interface) on your NAS, Raspberry Pi, macOS or wherever you want to bundle it really!

The subtitles search is done by precisly **identifying your video files** by computing unique movie hash sums. This way, you have more chance to find the **exact subtitles for your videos**, avoiding synchronization problems between the subtitles and the soundtrack. But what if that doesn't work? Well, a search with the filename will be performed, but be aware: results are a bit more... unpredictable (don't worry, you will be warned! and you can even disable this feature if you want).

The subtitles search and download service is powered by [opensubtitles.org](https://www.opensubtitles.org). Big thanks to their hard work on this amazing project! Be sure to [give them your support](http://www.opensubtitles.org/en/support) if you appreciate the service provided, they sure need donations for handling the ever growing hosting costs!

Features
--------

- Use a GNOME/GTK or KDE/Qt GUI depending on your favorite desktop environment
- Or just use the CLI! Great for automation, and it works on Linux, macOS and Windows
- Query subtitles in more than 60 different languages for documentaries, movies, TV shows and more...
- Query subtitles in multiple languages at once
- Query subtitles for multiple video files and folders at once
- Detect valid video files (using mime types and file extensions)
- Detect correct video titles by computing unique movie hash sums in order to download the right subtitles for the right file!
- If the video detection fails, a backup search using filename will be performed
- Download subtitles automatically if only one is available, choose the one you want otherwise
- Rename downloaded subtitles to match source video file. Possibility to append a language code to the file name (ex: movie_en.srt).

Requirements
------------

- python (version 2 or 3)
- zenity (only needed for GNOME based desktop environments)
- kdialog (only needed for KDE based desktop environments)
- common unix tools (only needed for GUIs): wget & gzip (GUI subtitles downloading), ps & grep (GUI autodetection)

Installation
------------

Quick installation as a nautilus script, under GNOME 3 desktop environment:

> $ mkdir -p ~/.local/share/nautilus/scripts/  
> $ cd ~/.local/share/nautilus/scripts/  
> $ wget https://raw.githubusercontent.com/emericg/OpenSubtitlesDownload/master/OpenSubtitlesDownload.py  
> $ chmod u+x OpenSubtitlesDownload.py  

Website
-------

You can browse the project's website at <https://emeric.io/OpenSubtitlesDownload.html>  
You can browse the project's GitHub page at <https://github.com/emericg/OpenSubtitlesDownload>  
Learn much more about OpenSubtitlesDownload.py installation and configuration on its wiki at <https://github.com/emericg/OpenSubtitlesDownload/wiki>  

Screenshots!
------------

![Start subtitles search](https://raw.githubusercontent.com/emericg/OpenSubtitlesDownload/screenshots/osd_screenshot_launch.png)

![Download selected subtitles](https://raw.githubusercontent.com/emericg/OpenSubtitlesDownload/screenshots/osd_screenshot_autodownload.png)

Enjoy your subtitled video!
![Enjoy your subtitled video!](https://raw.githubusercontent.com/emericg/OpenSubtitlesDownload/screenshots/enjoy-sintel.jpg)

What if multiple subtitles are available? Just pick one from the list!
![Multiple subtitles selection](https://raw.githubusercontent.com/emericg/OpenSubtitlesDownload/screenshots/osd_screenshot_selection.png)

Contributors
------------

- Emeric Grange <emeric.grange@gmail.com> maintainer
- Thiago Alvarenga Lechuga <thiagoalz@gmail.com> for his work on the 'Windows CLI' and the 'folder search'
- jeroenvdw for his work on the 'subtitles automatic selection' and the 'search by filename'
- Gui13 for his work on the arguments parsing
- Tomáš Hnyk <tomashnyk@gmail.com> for his work on the 'multiple language' feature
- Carlos Acedo <carlos@linux-labs.net> for his work on the original script

License
-------

OpenSubtitlesDownload.py is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.  
Read the license [on the FSF website](https://www.gnu.org/licenses/gpl-3.0.txt).
