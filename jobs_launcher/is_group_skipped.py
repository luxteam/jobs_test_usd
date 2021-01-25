import argparse
import os
import json
import sys

from core.countLostTests import PLATFORM_CONVERTATIONS
from jobs.Scripts.utils import is_case_skipped


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--gpu', required=True)
    parser.add_argument('--os', required=True)
    parser.add_argument('--engine', required=False)
    parser.add_argument('--tests_path', required=True)

    args = parser.parse_args()

    with open(args.tests_path) as file:
        cases = json.load(file)

    render_platform = {PLATFORM_CONVERTATIONS[args.os]["os_name"], PLATFORM_CONVERTATIONS[args.os]["cards"][args.gpu]}

    skipped_cases_num = 0
    total_cases_num = len(cases)

    for case in cases:
        if args.engine:	
            case_skipped = is_case_skipped(case, render_platform, args.engine)
        else:
            case_skipped = is_case_skipped(case, render_platform)
        if case_skipped:
            skipped_cases_num += 1
    print(skipped_cases_num == total_cases_num)
