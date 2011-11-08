#!/usr/bin/python
# -*- coding: utf-8 -*-

# OpenSubtitles download - (Gnome edition)
# version 1.1
#
# Automatically find and download subtitles from opensubtitles.org !

# Emeric Grange <emeric.grange@gmail.com>
# Carlos Acedo <carlos@linux-labs.net> for the original script

# Copyright (c) 2011 by Emeric GRANGE <emeric.grange@gmail.com>
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

import os
import struct
import subprocess
import mimetypes
from sys import argv
from xmlrpclib import ServerProxy, Error

# ==== Language selection ======================================================
# Default language is english. You can change the 'SubLanguageID' by using any 
# valid 'ISO 639-3' or 'ISO 639-2' language code.
# ISO codes list : http://en.wikipedia.org/wiki/List_of_ISO_639-2_codes
SubLanguageID = 'eng'

# ==== Server selection ========================================================
# Xml-rpc API server domain of opensubtitles.org
server = ServerProxy('http://api.opensubtitles.org/xml-rpc')

# ==== Check file type =========================================================
def checkFile(path):
    """Check mimetype and/or file extension to detect valid video file"""
    if os.path.isfile(path) == False:
        #subprocess.call(['zenity', '--error', '--text=This is not a file :\n- ' + path])
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
            #subprocess.call(['zenity', '--error', '--text=This file is not a video :\n- (unknown mimetype AND bad extension)\n- ' + path])
            return False
    else:
        fileMimeType = fileMimeType.split('/', 1)
        if fileMimeType[0] != 'video':
            #subprocess.call(['zenity', '--error', '--text=This file is not a video :\n- (unknown mimetype)\n- ' + path])
            return False
    
    return True

# ==== Hashing algorithm =======================================================
# Source : http://trac.opensubtitles.org/projects/opensubtitles/wiki/HashSourceCodes
# This particular implementation is from SubDownloader
def hashFile(path):
    """Produce a hash for a video file : size + 64bit chksum of the first and 
    last 64k (even if they overlap because the file is smaller than 128k)"""
    try:
        longlongformat = 'Q' # unsigned long long little endian
        bytesize = struct.calcsize(longlongformat)
        format = "<%d%s" % (65536//bytesize, longlongformat)
        
        f = open(path, "rb")
        
        filesize = os.fstat(f.fileno()).st_size
        hash = filesize
        
        if filesize < 65536 * 2:
            subprocess.call(['zenity', '--error', '--text=Size error while generating hash for this file :\n- ' + path])
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
        subprocess.call(['zenity', '--error', '--text=Input/Output error while generating hash for this file :\n- ' + path])
        return "IOError"

# ==== Get file(s) path(s) =====================================================
# Get opensubtitles-download script path, then remove it from argv list
execPath = argv[0]
argv.pop(0)

filePathList = []
moviePathList = []
moviePath = ''

if len(argv) == 0:
    #subprocess.call(['zenity', '--error', '--text=No file selected.'])
    exit(1)
elif argv[0] == '--file':
    moviePath = argv[1]
else:
    # Put file(s) path(s) in filePathList
    try:
        filePathList = os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].splitlines()
    except Exception:
        try:
            for i in range(len(argv)):
                if os.path.isabs(argv[i]) == False:
                    filePathList.append(os.getcwd() + '/' + argv[i])
                else:
                    filePathList.append(argv[i])
        except Exception:
            #subprocess.call(['zenity', '--error', '--text=Bug in the filepath given in parameter.'])
            exit(1)
    
    # Check file(s) type
    for i in range(len(filePathList)):
        if checkFile(filePathList[i]):
            moviePathList.append(filePathList[i])
    
    # If moviePathList is empty, abort
    if len(moviePathList) == 0:
        exit(1)
    
    # Dispatch file(s)
    moviePath = moviePathList[0]
    moviePathList.pop(0)
    for i in range(len(moviePathList)):
        op_dispatchedvideo = subprocess.Popen(execPath + ' --file \'' + moviePathList[i] + '\'', shell=True)

# ==== Main program ============================================================
try:
    try:
        # Connection to opensubtitles.org server
        session = server.LogIn('', '', 'en', 'opensubtitles-download 1.1')
        if session['status'] != '200 OK':
            subprocess.call(['zenity', '--error', '--text=Unable to reach opensubtitles.org server : ' + session['status'] + '. Please check :\n- Your internet connection\n- www.opensubtitles.org availability'])
            exit(1)
        token = session['token']
    except Exception:
        subprocess.call(['zenity', '--error', '--text=Unable to reach opensubtitles.org server. Please check :\n- Your internet connection\n- www.opensubtitles.org availability'])
        exit(1)
    
    movieHash = hashFile(moviePath)
    movieSize = os.path.getsize(moviePath)
    
    # Search for available subtitles
    searchList = []
    searchList.append({'sublanguageid':SubLanguageID, 'moviehash':movieHash, 'moviebytesize':str(movieSize)}) # Search movie by file hash
    #searchList.append({'sublanguageid':SubLanguageID, 'query':moviePath}) # Search movie by file name
    subtitlesList = server.SearchSubtitles(token, searchList)
    
    if subtitlesList['data']:
        # Sanitize title strings to avoid parsing errors
        for item in subtitlesList['data']:
            item['MovieName'] = item['MovieName'].replace('"', '')
            item['MovieName'] = item['MovieName'].replace("'", '')
        
        # If there is more than one subtitle, let the user decided wich one will be downloaded
        if len(subtitlesList['data']) != 1:
            subtitleItems = ''
            for item in subtitlesList['data']:
                subtitleItems += '"' + item['SubFileName'] + '" '
            op_subtitleselection = subprocess.Popen('zenity --width=600 --height=256 --list --title="' + item['MovieName'] + '" --column="Available subtitle(s)" ' + subtitleItems, shell=True, bufsize=256, stdout=subprocess.PIPE)
            
            subtitleSelected = str(op_subtitleselection.communicate()[0]).strip('\n')
            resp = op_subtitleselection.returncode
        else:
            subtitleSelected = ''
            resp = 0
        
        if resp == 0:
            # Select subtitle file to download
            index = 0
            subIndex = 0
            for item in subtitlesList['data']:
                if item['SubFileName'] == subtitleSelected:
                    subIndex = index
                else:
                    index = 1
            
            subDirName = os.path.dirname(moviePath)
            subURL = subtitlesList['data'][subIndex]['SubDownloadLink']
            subFileName = os.path.basename(moviePath)[:-3] + subtitlesList['data'][subIndex]['SubFileName'][-3:]
            
            # Download and unzip selected subtitle (with progressbar)
            op_download = subprocess.call('(wget -O - ' + subURL + ' | gunzip > "' + subDirName + '/' + subFileName + '") 2>&1 | zenity --progress --pulsate --title="Downloading subtitle, please wait..." --text="Downloading subtitle for \'' + subtitlesList['data'][0]['MovieName'] + '\' : "', shell=True)
            
            # If an error occur, say so
            if op_download != 0:
                subprocess.call(['zenity', '--error', '--text=An error occurred while downloading or writing the selected subtitle.'])
    else:
        movieFileName = moviePath.rsplit('/', -1)
        subprocess.call(['zenity', '--info', '--title=No subtitle found', '--text=No subtitle found for this video :\n- ' + movieFileName[-1]])
    
    # Disconnect from opensubtitles.org server, then exit
    server.LogOut(token)
    exit(0)
except Error:
    # If an unknown error occur, say so and apologize
    subprocess.call(['zenity', '--error', '--text=An unknown error occurred, sorry about that...'])
    exit(1)

