import argparse
import shutil
import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import core.config
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, os.path.pardir)))
    from local_config import *
except ImportError:
    core.config.main_logger.critical("local config file not found. Default values will be used.")
    core.config.main_logger.critical("Correct report building isn't guaranteed")
    from core.defaults_local_config import *



def create_args_parser():
    args = argparse.ArgumentParser()
    args.add_argument('--remove_old', default=False)
    args.add_argument('--results_root', default='Work\Results\Core')
    args.add_argument('--baseline_root', default='Work\Baseline')
    args.add_argument('--case_suffix', required=False, default=core.config.TEST_REPORT_NAME_COMPARED)
    return args


if __name__ == '__main__':
    args = create_args_parser()
    args = args.parse_args()

    args.results_root = os.path.abspath(args.results_root)
    args.baseline_root = os.path.abspath(args.baseline_root)

    report = []
    if os.path.exists(args.baseline_root) and args.remove_old:
        shutil.rmtree(args.baseline_root)

    # find and process report_compare.json files
    for path, dirs, files in os.walk(args.results_root):
        for file in files:
            if file.endswith(args.case_suffix):
                # create destination folder in baseline location
                if not os.path.exists(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root))):
                    os.makedirs(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root)))
                # copy json report with new names
                with open(os.path.join(path, file)) as f:
                    cases = json.load(f)
                for case in cases:
                    # remove odd fields
                    for field in core.config.ODD_FOR_BASELINES:
                        case.pop(field, None)

                    if case.get('test_status', core.config.TEST_IGNORE_STATUS) != core.config.TEST_CRASH_STATUS:
                        with open(os.path.join(args.baseline_root, os.path.relpath(path, args.results_root), case['test_case'] + core.config.CASE_REPORT_SUFFIX), 'w') as f:
                            f.write(json.dumps(case, indent=4))

                        # copy rendered images and thumbnails
                        for img in core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS_THUMBNAIL + core.config.POSSIBLE_JSON_IMG_RENDERED_KEYS:
                            if img in case.keys():
                                rendered_img_path = os.path.join(path, case[img])
                                baseline_img_path = os.path.relpath(rendered_img_path, args.results_root)

                                # create folder in first step for current folder
                                if not os.path.exists(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0])):
                                    os.makedirs(os.path.join(args.baseline_root, os.path.split(baseline_img_path)[0]))

                                try:
                                    shutil.copyfile(rendered_img_path,
                                                    os.path.join(args.baseline_root, baseline_img_path))
                                except IOError as err:
                                    core.config.main_logger.warning("Error baseline copy file: {}".format(str(err)))
