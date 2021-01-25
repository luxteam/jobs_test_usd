#!/bin/bash
GPU="$1"
OS="$2"
ENGINE="$3"
TESTS_PATH="$4"

python core/isGroupSkipped.py --gpu $GPU --os $OS --engine $ENGINE --tests_path $TESTS_PATH
