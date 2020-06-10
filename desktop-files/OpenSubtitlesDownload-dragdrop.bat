echo off

set files=%*

REM Set the correct path to your OpenSubtitlesDownload.py executable here
python "C:\OpenSubtitlesDownload.py" --cli -a %files%

@pause
