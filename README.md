## Introduction

This little software, written in python, is built to help you quickly find and download subtitles for your favorite videos. It can be used as a nautilus script, or as a regular application working under GNOME or KDE desktop environments. You can also use it in full console mode!

The subtitles are downloaded from opensubtitles.org. The search is done by precisely identifying your videos using a hash computed from your files, and not by using filenames. This way, you have more chance to get the exact subtitles corresponding to your videos, avoiding synchronization problems between the subtitles and the soundtrack.

Subtitles service is powered by www.opensubtitles.org. Big thanks to their hard work on this amazing project! Be sure to give them your support if you appreciate the service provided.

## Installation

### Installation as a nautilus script, under Gnome 3 desktop environment

mkdir -p ~/.local/share/nautilus/scripts/
cp gnome/opensubtitles-download.py ~/.local/share/nautilus/scripts/opensubtitles-download.py
chmod u+x ~/.local/share/nautilus/scripts/opensubtitles-download.py
