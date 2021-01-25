set PATH=c:\python35\;c:\python35\scripts\;%PATH%

set FILES_PATH=%1
set PATTERN=%2

python send_to_minio.py --files_path %FILES_PATH% --pattern %PATTERN%