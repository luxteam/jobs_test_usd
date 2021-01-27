set PATH=c:\python35\;c:\python35\scripts\;%PATH%
set FILE_FILTER=%1
set TESTS_FILTER="%2"
set RX=%3
set RY=%4
set DELEGATE=%5
set TOOL=%6
set RETRIES=%7
set UPDATE_REFS=%8

if not defined RX set RX=0
if not defined RY set RY=0
if not defined DELEGATE set DELEGATE="HdRprPlugin"
if not defined TOOL set TOOL=2.91
if not defined RETRIES set RETRIES=2
if not defined UPDATE_REFS set UPDATE_REFS="No"

python -m pip install -r ../jobs_launcher/install/requirements.txt

python ..\jobs_launcher\executeTests.py --test_filter %TESTS_FILTER% --file_filter %FILE_FILTER% --tests_root ..\jobs --work_root ..\Work\Results --work_dir Blender28 --cmd_variables Tool "C:\Program Files\Blender Foundation\Blender %TOOL%\blender.exe" ResPath "C:\TestResources\Blender2.8Assets" rx %RX% ry %RY% delegate %DELEGATE% retries %RETRIES% UpdateRefs %UPDATE_REFS%
