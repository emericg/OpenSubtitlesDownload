OpenSubtitlesDownload.py
========================

Introduction
------------

This little software, written in python, is built to help you quickly find and download subtitles for your favorite videos. It can be used as a nautilus script, or as a regular application working under GNOME or KDE desktop environments. You can also use it in full console mode!

The subtitles are downloaded from opensubtitles.org. The search is done by precisely identifying your videos using a hash computed from your files, and not by using filenames. This way, you have more chance to get the exact subtitles corresponding to your videos, avoiding synchronization problems between the subtitles and the soundtrack.

Subtitles service is powered by www.opensubtitles.org. Big thanks to their hard work on this amazing project! Be sure to give them your support if you appreciate the service provided.

Features
--------

- Query subtitles in more than 60 different languages for documentaries, movies, TV shows and more...
- Query subtitles in multiple languages at once.
- Select multiple video files to search their subtitles simultaneously.
- Select different target languages to search them simultaneously.
- Detect valid video files (using mime types and file extensions).
- Detect correct video titles by computing hash file signatures, not by reading the filenames.
- Download subtitles automatically if only one is available, select the one you want otherwise.
- Rename downloaded subtitles to match source video file. Possibility to append the language code to the file name (ex: movie_en.srt).

Requirements
------------

- python (version 2 or 3)
- wget & gzip
- zenity (Gnome 2/3 or Xfce desktop environments)

Installation
------------

Quick installation as a nautilus script, under Gnome 3 desktop environment:

> $ git clone https://github.com/emericg/opensubtitles-download.git  
> $ mkdir -p ~/.local/share/nautilus/scripts/  
> $ cp opensubtitles-download/gnome/opensubtitles-download.py ~/.local/share/nautilus/scripts/opensubtitles-download.py  
> $ chmod u+x ~/.local/share/nautilus/scripts/opensubtitles-download.py  

Website
-------

You can browse the project's GitHub page and wiki at <https://github.com/emericg/opensubtitles-download>.

License
-------

GPL v3 <http://www.gnu.org/licenses/gpl-3.0.txt>
