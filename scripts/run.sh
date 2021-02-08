#!/bin/bash
FILE_FILTER=$1
TESTS_FILTER="$2"
RX=${3:-0}
RY=${4:-0}
DELEGATE=${5:-HdRprPlugin}
TOOL=${6:-2.91}
RETRIES=${7:-2}
UPDATE_REFS=${8:-No}
python -m pip install --user -r ../jobs_launcher/install/requirements.txt

python ../jobs_launcher/executeTests.py --test_filter $TESTS_FILTER --file_filter $FILE_FILTER --tests_root ../jobs --work_root ../Work/Results --work_dir BlenderUSDHydra --cmd_variables Tool "blender$TOOL" ResPath "$CIS_TOOLS/../TestResources/BlenderUSDHydraAssets" rx $RX ry $RY delegate $DELEGATE retries $RETRIES UpdateRefs $UPDATE_REFS
