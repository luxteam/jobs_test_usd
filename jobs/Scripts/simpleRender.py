import argparse
import os
import subprocess
import psutil
import json
import ctypes
import pyscreenshot
import platform
from datetime import datetime
from shutil import copyfile, move, which
import sys
import re
import time
from threading import Thread, Lock
from utils import is_case_skipped

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import jobs_launcher.core.performance_counter as perf_count
import jobs_launcher.core.config as core_config
from jobs_launcher.core.system_info import get_gpu
from jobs_launcher.core.kill_process import kill_process


ROOT_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir))
PROCESS = ['blender', 'blender.exe', 'Blender']


stop_threads = False
render_log_lock = Lock()


def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument('--tool', required=True, metavar="<path>")
    parser.add_argument('--render_device', required=True)
    parser.add_argument('--output', required=True, metavar="<dir>")
    parser.add_argument('--testType', required=True)
    parser.add_argument('--res_path', required=True)
    parser.add_argument('--resolution_x', required=True)
    parser.add_argument('--resolution_y', required=True)
    parser.add_argument('--pass_limit', required=True)
    parser.add_argument('--testCases', required=True)
    parser.add_argument('--SPU', required=False, default=25)
    parser.add_argument('--engine', required=False, default='FULL')
    parser.add_argument('--error_count', required=False, default=0, type=int)
    parser.add_argument('--threshold', required=False,
                        default=0.05, type=float)
    parser.add_argument('--retries', required=False, default=2, type=int)
    parser.add_argument('--update_refs', required=True)

    return parser


def start_logs_daemon(output_file, std):
    for line in iter(std.readline, b''):
        if stop_threads: 
            return
        while render_log_lock.locked():
            continue
        render_log_lock.acquire()
        with open(output_file, 'a', encoding='utf-8') as file:
            file.write(line.decode("utf-8"))
        render_log_lock.release()


def rename_log(old_name, new_name):
    try:
        move(os.path.join(os.path.abspath(args.output), old_name),
             os.path.join(os.path.abspath(args.output), new_name))
    except Exception as e:
        core_config.main_logger.warning('No {}'.format(old_name))


def get_finished_cases_number(output):
    for i in range(3):
        try:
            with open(os.path.join(os.path.abspath(output), 'test_cases.json')) as file:
                test_cases = json.load(file)
                return len([case['status'] for case in test_cases if case['status'] in ('skipped', 'error', 'done')])
        except Exception as e:
            core_config.main_logger.error('Failed to get number of finished cases (try #{}): Reason: {}'.format(i, str(e)))
            time.sleep(5)
    return -1


def athena_disable(disable, tool):
    tool_version = None
    for part in os.path.normpath(tool).split(os.sep):
        if re.match(".*[\d.]+.*", part):
            tool_version = re.search("[\d.]+", part).group(0)
            break
    if not tool_version:
        main_logger.error("Can't get tool version!")
    if (platform.system() == 'Windows'):
        CONFIG_PATH = os.path.expandvars(
            '%appdata%/Blender Foundation/Blender/{}/scripts/addons/rprblender/config.py'.format(tool_version))
        ATHENA_DIR = os.path.expandvars('%appdata%/../Local/Temp/rprblender/')
    elif (platform.system() == 'Darwin'):
        CONFIG_PATH = os.path.expanduser(
            '~/Library/Application Support/Blender/{}/scripts/addons/rprblender/config.py'.format(tool_version))
        ATHENA_DIR = os.environ['TMPDIR'] + 'rprblender/'
    else:
        CONFIG_PATH = os.path.expanduser(
            '~/.config/blender/{}/scripts/addons/rprblender/config.py'.format(tool_version))
        ATHENA_DIR = '/tmp/rprblender/'

    config_file_new = ''

    with open(CONFIG_PATH, 'r') as config_file:
        config_file_new = config_file.read().replace('disable_athena_report = ' + str(not disable), 'disable_athena_report = ' + str(disable))
    with open(CONFIG_PATH, 'w') as config_file:
        config_file.write(config_file_new)

    return ATHENA_DIR


def main(args):
    perf_count.event_record(args.output, 'Prepare tests', True)

    if args.testType in ['Athena']:
        ATHENA_DIR = athena_disable(False, args.tool)
    else:
        ATHENA_DIR = athena_disable(True, args.tool)

    core_config.main_logger.info('Make "base_functions.py"')

    try:
        cases = json.load(open(os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json'))))
    except Exception as e:
        core_config.main_logger.error("Can't load test_cases.json")
        core_config.main_logger.error(str(e))
        group_failed(args)
        exit(-1)

    try:
        with open(os.path.join(os.path.dirname(__file__), 'base_functions.py')) as f:
            script = f.read()
    except OSError as e:
        core_config.main_logger.error(str(e))
        return 1

    if os.path.exists(os.path.join(os.path.dirname(__file__), 'extensions', args.testType + '.py')):
        with open(os.path.join(os.path.dirname(__file__), 'extensions', args.testType + '.py')) as f:
            extension_script = f.read()
        script = script.split('# place for extension functions')
        script = script[0] + "ATHENA_DIR=\"{}\"\n".format(ATHENA_DIR.replace('\\', '\\\\')) + extension_script + script[1]

    work_dir = os.path.abspath(args.output)
    script = script.format(work_dir=work_dir, testType=args.testType, render_device=args.render_device, res_path=args.res_path, pass_limit=args.pass_limit,
                           resolution_x=args.resolution_x, resolution_y=args.resolution_y, SPU=args.SPU, threshold=args.threshold, engine=args.engine,
                           retries=args.retries)

    with open(os.path.join(args.output, 'base_functions.py'), 'w') as file:
        file.write(script)

    if os.path.exists(args.testCases) and args.testCases:
        with open(args.testCases) as f:
            test_cases = json.load(f)['groups'][args.testType]
            if test_cases:
                necessary_cases = [
                    item for item in cases if item['case'] in test_cases]
                cases = necessary_cases

    core_config.main_logger.info('Create empty report files')

    if not os.path.exists(os.path.join(work_dir, 'Color')):
        os.makedirs(os.path.join(work_dir, 'Color'))
    copyfile(os.path.abspath(os.path.join(work_dir, '..', '..', '..', '..', 'jobs_launcher',
                                          'common', 'img', 'error.jpg')), os.path.join(work_dir, 'Color', 'failed.jpg'))

    gpu = get_gpu()
    if not gpu:
        core_config.main_logger.error("Can't get gpu name")
    render_platform = {platform.system(), gpu}
    system_pl = platform.system()

    baseline_dir = 'rpr_blender_autotests_baselines'
    if args.engine == 'FULL2':
        baseline_dir = baseline_dir + '-NorthStar'
    elif args.engine == 'LOW':
        baseline_dir = baseline_dir + '-HybridLow'
    elif args.engine == 'MEDIUM':
        baseline_dir = baseline_dir + '-HybridMedium'
    elif args.engine == 'HIGH':
        baseline_dir = baseline_dir + '-HybridHigh'

    if system_pl == "Windows":
        baseline_path_tr = os.path.join(
            'c:/TestResources', baseline_dir, args.testType)
    else:
        baseline_path_tr = os.path.expandvars(os.path.join(
            '$CIS_TOOLS/../TestResources', baseline_dir, args.testType))

    baseline_path = os.path.join(
        work_dir, os.path.pardir, os.path.pardir, os.path.pardir, 'Baseline', args.testType)

    if not os.path.exists(baseline_path):
        os.makedirs(baseline_path)
        os.makedirs(os.path.join(baseline_path, 'Color'))

    for case in cases:
        if is_case_skipped(case, render_platform, args.engine):
            case['status'] = 'skipped'

        if case['status'] != 'done' and case['status'] != 'error':
            if case["status"] == 'inprogress':
                case['status'] = 'active'
                case['number_of_tries'] = case.get('number_of_tries', 0) + 1

            template = core_config.RENDER_REPORT_BASE.copy()
            template['test_case'] = case['case']
            template['case_functions'] = case['functions']
            template['render_device'] = get_gpu()
            template['script_info'] = case['script_info']
            template['scene_name'] = case.get('scene', '')
            template['test_group'] = args.testType
            template['date_time'] = datetime.now().strftime(
                '%m/%d/%Y %H:%M:%S')
            if case['status'] == 'skipped':
                template['test_status'] = 'skipped'
                template['file_name'] = case['case'] + case.get('extension', '.jpg')
                template['render_color_path'] = os.path.join('Color', template['file_name'])
                template['group_timeout_exceeded'] = False

                try:
                    skipped_case_image_path = os.path.join(args.output, 'Color', template['file_name'])
                    if not os.path.exists(skipped_case_image_path):
                        copyfile(os.path.join(work_dir, '..', '..', '..', '..', 'jobs_launcher', 
                            'common', 'img', "skipped.jpg"), skipped_case_image_path)
                except OSError or FileNotFoundError as err:
                    core_config.main_logger.error("Can't create img stub: {}".format(str(err)))
            else:
                template['test_status'] = 'error'
                template['file_name'] = 'failed.jpg'
                template['render_color_path'] = os.path.join('Color', 'failed.jpg')

            with open(os.path.join(work_dir, case['case'] + core_config.CASE_REPORT_SUFFIX), 'w') as f:
                f.write(json.dumps([template], indent=4))

        if 'Update' not in args.update_refs:
            try:
                copyfile(os.path.join(baseline_path_tr, case['case'] + core_config.CASE_REPORT_SUFFIX),
                         os.path.join(baseline_path, case['case'] + core_config.CASE_REPORT_SUFFIX))

                with open(os.path.join(baseline_path, case['case'] + core_config.CASE_REPORT_SUFFIX)) as baseline:
                    baseline_json = json.load(baseline)

                for thumb in [''] + core_config.THUMBNAIL_PREFIXES:
                    if thumb + 'render_color_path' and os.path.exists(os.path.join(baseline_path_tr, baseline_json[thumb + 'render_color_path'])):
                        copyfile(os.path.join(baseline_path_tr, baseline_json[thumb + 'render_color_path']),
                                 os.path.join(baseline_path, baseline_json[thumb + 'render_color_path']))
            except:
                core_config.main_logger.error('Failed to copy baseline ' +
                                              os.path.join(baseline_path_tr, case['case'] + core_config.CASE_REPORT_SUFFIX))

    with open(os.path.join(work_dir, 'test_cases.json'), "w+") as f:
        json.dump(cases, f, indent=4)

    cmdRun = '"{tool}" -b -P "{template}"\n'.format(
        tool=args.tool, template=os.path.join(args.output, 'base_functions.py'))

    if system_pl == "Windows":
        cmdScriptPath = os.path.join(work_dir, 'script.bat')
        with open(cmdScriptPath, 'w') as f:
            f.write(cmdRun)
    else:
        cmdScriptPath = os.path.join(work_dir, 'script.sh')
        with open(cmdScriptPath, 'w') as f:
            f.write(cmdRun)
        os.system('chmod +x {}'.format(cmdScriptPath))

    if which(args.tool) is None:
        core_config.main_logger.error('Can\'t find tool ' + args.tool)
        exit(-1)

    perf_count.event_record(args.output, 'Prepare tests', False)

    core_config.main_logger.info(
        'Launch script on Blender ({})'.format(cmdScriptPath))
    perf_count.event_record(args.output, 'Open tool', True)

    p = subprocess.Popen(cmdScriptPath, shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    prev_done_test_cases = get_finished_cases_number(args.output)

    stdout = []
    stdout_thread = Thread(target=start_logs_daemon, args=(os.path.join(args.output, "renderToolRaw.log"), p.stdout))
    stdout_thread.daemon = True
    stdout_thread.start()

    stderr = []
    stderr_thread = Thread(target=start_logs_daemon, args=(os.path.join(args.output, "renderToolRaw.log"), p.stderr))
    stderr_thread.daemon = True
    stderr_thread.start()

    rc = None

    timeout=420
    while rc is None:
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() <= timeout:
            time.sleep(1)
            if p.poll() is not None:
                rc = 0
                break
        else:
            new_done_test_cases_num = get_finished_cases_number(args.output)
            if new_done_test_cases_num == -1:
                core_config.main_logger.error('Failed to get number of finished cases. Try to do that on next iteration')
            elif prev_done_test_cases == new_done_test_cases_num:
                # if number of finished cases wasn't increased - Blender got stuck
                core_config.main_logger.error('Blender got stuck.')
                rc = -1
                p.terminate()
                time.sleep(10)
                p.kill()
                break
            else:
                prev_done_test_cases = new_done_test_cases_num
    stop_threads = True

    perf_count.event_record(args.output, 'Close tool', False)

    # TODO: check athena work in blender

    return rc


def group_failed(args):
    core_config.main_logger.error('Group failed')
    status = 'skipped'
    try:
        cases = json.load(open(os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json'))))
    except Exception as e:
        core_config.logging.error("Can't load test_cases.json")
        core_config.main_logger.error(str(e))
        cases = json.load(open(os.path.realpath(os.path.join(os.path.dirname(
            __file__), '..', 'Tests', args.testType, 'test_cases.json'))))
        status = 'inprogress'

    for case in cases:
        if case['status'] == 'active':
            case['status'] = status

    with open(os.path.join(os.path.abspath(args.output), 'test_cases.json'), "w+") as f:
        json.dump(cases, f, indent=4)

    rc = main(args)
    kill_process(PROCESS)
    core_config.main_logger.info(
        "Finish simpleRender with code: {}".format(rc))
    exit(rc)


if __name__ == "__main__":
    core_config.main_logger.info("simpleRender start working...")

    args = createArgsParser().parse_args()

    iteration = 0

    try:
        os.makedirs(args.output)
    except OSError as e:
        pass

    try:
        copyfile(os.path.realpath(os.path.join(os.path.dirname(
            __file__), '..', 'Tests', args.testType, 'test_cases.json')),
            os.path.realpath(os.path.join(os.path.abspath(
                args.output), 'test_cases.json')))
    except:
        core_config.logging.error("Can't copy test_cases.json")
        core_config.main_logger.error(str(e))
        exit(-1)

    while True:
        iteration += 1

        core_config.main_logger.info(
            'Try to run script in blender (#' + str(iteration) + ')')

        rc = main(args)

        try:
            cases = json.load(open(os.path.realpath(
                os.path.join(os.path.abspath(args.output), 'test_cases.json'))))
        except Exception as e:
            core_config.logging.error("Can't load test_cases.json")
            core_config.main_logger.error(str(e))
            exit(-1)

        active_cases = 0
        current_error_count = 0

        for case in cases:
            if case['status'] in ['fail', 'error', 'inprogress']:
                current_error_count += 1
                if args.error_count == current_error_count:
                    group_failed(args)
            else:
                current_error_count = 0

            if case['status'] in ['active', 'fail', 'inprogress']:
                active_cases += 1

        if active_cases == 0 or iteration > len(cases) * args.retries:
            # exit script if base_functions don't change number of active cases
            kill_process(PROCESS)
            core_config.main_logger.info(
                "Finish simpleRender with code: {}".format(rc))
            exit(rc)
