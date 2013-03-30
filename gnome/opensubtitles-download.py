#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2013 by Emeric GRANGE <emeric.grange@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Contributors / special thanks:
# Tomáš Hnyk <tomashnyk@gmail.com> for his work on the 'multiple language' feature
# Carlos Acedo <carlos@linux-labs.net> for his work on the original script

# OpenSubtitles-download / GNOME edition / Version 3.0
# Automatically find and download subtitles for all of your favorite videos!
# Website: https://github.com/emericg/opensubtitles-download

import os
import struct
import mimetypes
import subprocess
import sys

if sys.version_info >= (3,0):
    from xmlrpc.client import ServerProxy, Error
else: # python2
    from xmlrpclib import ServerProxy, Error

# ==== Language selection ======================================================
# Supported ISO codes: http://www.opensubtitles.org/addons/export_languages.php

# 1/ You can change the search language here by using either 2-letter (ISO 639-1)
# or 3-letter (ISO 639-2) language codes.
# 2/ You can also search for subtitles in several languages ​​at once:
# - SubLanguageIDs = ['eng,fre'] to download the first language available only
# - SubLanguageIDs = ['eng','fre'] to download all selected languages

SubLanguageIDs = ['eng']

# ==== Settings ================================================================
# For a complete documentation of these options, please refer to the wiki.

# Change the subtitle selection GUI size:
gui_width  = 720
gui_height = 320

# Various GUI options. You can set them to 'on' or 'off' and sometimes 'auto' mode.
opt_file_languagecode  = 'off'
opt_selection_language = 'auto'
opt_selection_hi       = 'auto'
opt_selection_cd       = 'auto'
opt_selection_rating   = 'off'
opt_selection_count    = 'off'

# ==== Server selection ========================================================
# XML-RPC server domain for opensubtitles.org:
server = ServerProxy('http://api.opensubtitles.org/xml-rpc')

# ==== Check file path & file ==================================================
def checkFile(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) == False:
        #subprocess.call(['zenity', '--error', '--text=This is not a file:\n<i>' + path + '</i>'])
        return False
    
    fileMimeType, encoding = mimetypes.guess_type(path)
    if fileMimeType == None:
        fileExtension = path.rsplit('.', 1)
        if fileExtension[1] not in ['3g2', '3gp', '3gp2', '3gpp', 'ajp', \
        'asf', 'asx', 'avchd', 'avi', 'bik', 'bix', 'box', 'cam', 'dat', \
        'divx', 'dmf', 'dv', 'dvr-ms', 'evo', 'flc', 'fli', 'flic', 'flv', \
        'flx', 'gvi', 'gvp', 'h264', 'm1v', 'm2p', 'm2ts', 'm2v', 'm4e', \
        'm4v', 'mjp', 'mjpeg', 'mjpg', 'mkv', 'moov', 'mov', 'movhd', 'movie', \
        'movx', 'mp4', 'mpe', 'mpeg', 'mpg', 'mpv', 'mpv2', 'mxf', 'nsv', \
        'nut', 'ogg', 'ogm', 'ogv', 'omf', 'ps', 'qt', 'ram', 'rm', 'rmvb', \
        'swf', 'ts', 'vfw', 'vid', 'video', 'viv', 'vivo', 'vob', 'vro', \
        'webm', 'wm', 'wmv', 'wmx', 'wrap', 'wvx', 'wx', 'x264', 'xvid']:
            #subprocess.call(['zenity', '--error', '--text=This file is not a video (unknown mimetype AND invalid file extension):\n<i>' + path + '</i>'])
            return False
    else:
        fileMimeType = fileMimeType.split('/', 1)
        if fileMimeType[0] != 'video':
            #subprocess.call(['zenity', '--error', '--text=This file is not a video (unknown mimetype):\n<i>' + path + '</i>'])
            return False
    
    return True

# ==== Hashing algorithm =======================================================
# Infos: http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
# This particular implementation is coming from SubDownloader: http://subdownloader.net/
def hashFile(path):
    """Produce a hash for a video file: size + 64bit chksum of the first and 
    last 64k (even if they overlap because the file is smaller than 128k)"""
    try:
        longlongformat = 'Q' # unsigned long long little endian
        bytesize = struct.calcsize(longlongformat)
        format = "<%d%s" % (65536//bytesize, longlongformat)
        
        f = open(path, "rb")
        
        filesize = os.fstat(f.fileno()).st_size
        hash = filesize
        
        if filesize < 65536 * 2:
            subprocess.call(['zenity', '--error', '--text=File size error while generating hash for this file:\n<i>' + path + '</i>'])
            return "SizeError"
        
        buffer = f.read(65536)
        longlongs = struct.unpack(format, buffer)
        hash += sum(longlongs)
        
        f.seek(-65536, os.SEEK_END) # size is always > 131072
        buffer = f.read(65536)
        longlongs = struct.unpack(format, buffer)
        hash += sum(longlongs)
        hash &= 0xFFFFFFFFFFFFFFFF
        
        f.close()
        returnedhash = "%016x" % hash
        return returnedhash
    
    except IOError:
        subprocess.call(['zenity', '--error', '--text=Input/Output error while generating hash for this file:\n<i>' + path + '</i>'])
        return "IOError"

# ==== Get file(s) path(s) =====================================================
# Get opensubtitles-download script path, then remove it from argv list
execPath = argv[0]
argv.pop(0)
moviePath = ''

if len(argv) == 0:
    #subprocess.call(['zenity', '--error', '--text=No file selected.'])
    exit(1)
elif argv[0] == '--file':
    moviePath = argv[1]
else:
    filePathList = []
    moviePathList = []
    
    try:
        # Fill filePathList (using nautilus script)
        filePathList = os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].splitlines()
    except Exception:
        # Fill filePathList (using program arguments)
        for i in range(len(argv)):
            filePathList.append(os.path.abspath(argv[i]))
    
    # Check file(s) type
    for filePath in filePathList:
        if checkFile(filePath):
            moviePathList.append(filePath)
    
    # If moviePathList is empty, abort
    if len(moviePathList) == 0:
        exit(1)
    
    # The first file will be processed immediatly
    moviePath = moviePathList[0]
    moviePathList.pop(0)
    
    # The remaining file(s) are dispatched to new instance(s) of this script
    for moviePathDispatch in moviePathList:
        process_movieDispatched = subprocess.Popen([execPath, '--file', moviePathDispatch])

# ==== Main program ============================================================
try:
    try:
        # Connection to opensubtitles.org server
        session = server.LogIn('', '', 'en', 'opensubtitles-download 3.0')
        if session['status'] != '200 OK':
            subprocess.call(['zenity', '--error', '--text=Unable to reach opensubtitles.org server: ' + session['status'] + '.\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability'])
            exit(1)
        token = session['token']
    except Exception:
        subprocess.call(['zenity', '--error', '--text=Unable to reach opensubtitles.org server.\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability'])
        exit(1)
    
    searchLanguage = 0
    searchLanguageResult = 0
    movieHash = hashFile(moviePath)
    movieSize = os.path.getsize(moviePath)
    movieFileName = os.path.basename(moviePath)
    
    # Count languages
    for SubLanguageID in SubLanguageIDs:
        searchLanguage += len(SubLanguageID.split(','))
    
    # Search for subtitles
    for SubLanguageID in SubLanguageIDs:
        
        # Search for available subtitles (using file hash and file size)
        searchList = []
        searchList.append({'sublanguageid':SubLanguageID, 'moviehash':movieHash, 'moviebytesize':str(movieSize)})
        subtitlesList = server.SearchSubtitles(token, searchList)
        
        # Parse the results of the XML-RPC query
        if subtitlesList['data']:
            
            # Mark search as successful
            searchLanguageResult += 1
            
            # Sanitize the title string to avoid parsing errors
            for item in subtitlesList['data']:
                item['MovieName'] = item['MovieName'].replace('"', '\\"')
                item['MovieName'] = item['MovieName'].replace("'", "\'")
            
            # If there is more than one subtitles, let the user decide which one will be downloaded
            if len(subtitlesList['data']) != 1:
                subtitlesItems = ''
                columnLn = ''
                columnCd = ''
                columnHi = ''
                columnRate = ''
                columnCount = ''
                
                # Handle 'auto' options
                for item in subtitlesList['data']:
                    if opt_selection_language == 'auto':
                        if searchLanguage > 1:
                            opt_selection_language = 'on'
                    if opt_selection_cd == 'auto':
                        if item['SubSumCD'] != '1':
                            opt_selection_cd = 'on'
                    if opt_selection_hi == 'auto':
                        if item['SubHearingImpaired'] == '1':
                            opt_selection_hi = 'on'
                    if opt_selection_rating == 'auto':
                        if item['SubRating'] != '0.0':
                            opt_selection_rating = 'on'
                    if opt_selection_count == 'auto':
                        opt_selection_count = 'on'
                
                # Generate selection window content
                for item in subtitlesList['data']:
                    subtitlesItems += '"' + item['SubFileName'] + '" '
                    if opt_selection_language == 'on':
                        columnLn = '--column="Language" '
                        subtitlesItems += '"' + item['LanguageName'] + '" '
                    if opt_selection_cd == 'on':
                        columnCd = '--column="CD" '
                        subtitlesItems += '"' + item['SubSumCD'] + '" '
                    if opt_selection_hi == 'on':
                        columnHi = '--column="HI" '
                        if item['SubHearingImpaired'] == '1':
                            subtitlesItems += '"✓" '
                        else:
                            subtitlesItems += '"" '
                    if opt_selection_rating == 'on':
                        columnRate = '--column="Rating" '
                        subtitlesItems += '"' + item['SubRating'] + '" '
                    if opt_selection_count == 'on':
                        columnCount = '--column="Dl count" '
                        subtitlesItems += '"' + item['SubDownloadsCnt'] + '" '
                
                # Spawn selection window
                process_subtitlesSelection = subprocess.Popen('zenity --width=' + str(gui_width) + ' --height=' + str(gui_height) + ' --list --title="' + item['MovieName'] + ' (' + movieFileName + ')" --column="Available subtitles" ' + columnLn + columnCd + columnHi + columnRate + columnCount + subtitlesItems, shell=True, stdout=subprocess.PIPE)
                subtitlesSelected = str(process_subtitlesSelection.communicate()[0]).strip('\n')
                retcode = process_subtitlesSelection.returncode
            else:
                subtitlesSelected = ''
                retcode = 0
            
            if retcode != -1:
                subIndex = 0
                subIndexTemp = 0
                
                # Select the subtitles file to download
                for item in subtitlesList['data']:
                    if item['SubFileName'] == subtitlesSelected:
                        subIndex = subIndexTemp
                        break
                    else:
                        subIndexTemp += 1
                
                subLangId = '_' + subtitlesList['data'][subIndex]['ISO639']
                subLangName = subtitlesList['data'][subIndex]['LanguageName']
                subURL = subtitlesList['data'][subIndex]['SubDownloadLink']
                subPath = moviePath.rsplit('.', 1)[0] + '.' + subtitlesList['data'][subIndex]['SubFormat']
                
                # Write language code into the filename ?
                if (opt_file_languagecode == 'on' or \
                    opt_file_languagecode == 'auto' and searchLanguageResult > 1):
                    subPath = moviePath.rsplit('.', 1)[0] + subLangId + '.' + subtitlesList['data'][subIndex]['SubFormat']
                
                # Download and unzip the selected subtitles (with progressbar)
                process_subtitlesDownload = subprocess.call('(wget -O - ' + subURL + ' | gunzip > "' + subPath + '") 2>&1 | (zenity --auto-close --progress --pulsate --title="Downloading subtitles, please wait..." --text="Downloading <b>' + subtitlesList['data'][subIndex]['LanguageName'] + '</b> subtitles for <b>' + subtitlesList['data'][subIndex]['MovieName'] + '</b>")', shell=True)
                
                # If an error occur, say so
                if process_subtitlesDownload != 0:
                    subprocess.call(['zenity', '--error', '--text=An error occurred while downloading or writing <b>' + subtitlesList['data'][subIndex]['LanguageName'] + '</b> subtitles for <b>' + subtitlesList['data'][subIndex]['MovieName'] + '</b>".'])
                    exit(1)
    
    # Print a message if none of the subtitles languages have been found
    if searchLanguageResult == 0:
        subprocess.call(['zenity', '--info', '--title=No subtitles found for ' + movieFileName, '--text=No subtitles found for this video:\n<i>' + movieFileName + '</i>'])
    
    # Disconnect from opensubtitles.org server, then exit
    server.LogOut(token)
    exit(0)

except Error:
    # If an unknown error occur, say so (and apologize)
    subprocess.call(['zenity', '--error', '--text=An <b>unknown error</b> occurred, sorry about that...\n\nPlease check:\n- Your Internet connection status\n- www.opensubtitles.org availability'])
    exit(1)