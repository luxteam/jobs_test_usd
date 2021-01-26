#!/bin/bash
RENDER_DEVICE=$1
FILE_FILTER=$2
TESTS_FILTER="$3"
RX=${4:-0}
RY=${5:-0}
SPU=${6:-25}
ITER=${7:-50}
ENGINE=${8:-FULL}
TOOL=${9:-2.91}
RETRIES=${10:-2}
UPDATE_REFS=${11:-No}
python -m pip install --user -r ../jobs_launcher/install/requirements.txt

python ../jobs_launcher/executeTests.py --test_filter $TESTS_FILTER --file_filter $FILE_FILTER --tests_root ../jobs --work_root ../Work/Results --work_dir Blender28 --cmd_variables Tool "blender$TOOL" RenderDevice $RENDER_DEVICE ResPath "$CIS_TOOLS/../TestResources/Blender2.8Assets" PassLimit $ITER rx $RX ry $RY SPU $SPU engine $ENGINE retries $RETRIES UpdateRefs $UPDATE_REFS
