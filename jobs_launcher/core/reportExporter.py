import os
import subprocess
import jinja2
import json
import base64
from shutil import rmtree, copytree
from codecs import open
import datetime
import operator
from PIL import Image
import core.config as config
from core.config import *
from core.auto_dict import AutoDict
import copy
import sys
import traceback
import re
from glob import glob
from collections import OrderedDict
from core.countLostTests import PLATFORM_CONVERTATIONS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir)))

try:
    from local_config import *
except ImportError:
    main_logger.critical("local config file not found. Default values will be used.")
    main_logger.critical("Correct report building isn't guaranteed")
    from core.defaults_local_config import *


def save_json_report(report, session_dir, file_name, replace_pathsep=False):
    with open(os.path.abspath(os.path.join(session_dir, file_name)), "w", encoding='utf8') as file:
        if replace_pathsep:
            s = json.dumps(report, indent=4, sort_keys=True)
            file.write(s.replace(os.path.sep, '/'))
        else:
            json.dump(report, file, indent=4, sort_keys=True)


def save_html_report(report, session_dir, file_name, replace_pathsep=False):
    with open(os.path.abspath(os.path.join(session_dir, file_name)), "w", encoding='utf8') as file:
        if replace_pathsep:
            file.write(report.replace(os.path.sep, '/'))
        else:
            file.write(report)


def make_base64_img(session_dir, report):
    os.mkdir(os.path.join(session_dir, 'tmp'))

    for test_package in report['results']:
        for test_conf in report['results'][test_package]:
            for test_execution in report['results'][test_package][test_conf]['render_results']:

                for img in POSSIBLE_JSON_IMG_KEYS:
                    if img in test_execution:
                        try:
                            if not os.path.exists(os.path.abspath(test_execution[img])):
                                test_execution[img] = os.path.join(session_dir, test_execution[img])

                            cur_img = Image.open(os.path.abspath(test_execution[img]))
                            tmp_img = cur_img.resize((64, 64), Image.ANTIALIAS)
                            tmp_img.save(os.path.join(session_dir, 'tmp', 'img.jpg'))

                            with open(os.path.join(session_dir, 'tmp', 'img.jpg'), 'rb') as file:
                                code = base64.b64encode(file.read())

                            src = "data:image/jpeg;base64," + str(code)[2:-1]
                            test_execution.update({img: src})
                        except Exception as err:
                            traceback.print_exc()
                            main_logger.error('Error in base64 encoding: {}'.format(str(err)))

    return report


def env_override(value, key):
    return os.getenv(key, value)


def get_jobs_launcher_version(value):
    return subprocess.check_output("git describe --tags --always", shell=True).decode("utf-8")


def generate_thumbnails(session_dir):
    current_test_report = []
    main_logger.info("Start thumbnails creation")

    for path, dirs, files in os.walk(session_dir):
        for json_report in files:
            if json_report == TEST_REPORT_NAME_COMPARED:
                with open(os.path.join(path, json_report), 'r') as file:
                    current_test_report = json.loads(file.read())

                for test in current_test_report:
                    for img_key in POSSIBLE_JSON_IMG_KEYS:
                        if img_key in test.keys():
                            try:
                                cur_img_path = os.path.abspath(os.path.join(path, test[img_key]))
                                thumb64_path = os.path.abspath(
                                    os.path.join(path, test[img_key].replace(test['test_case'],
                                                                             'thumb64_' + test['test_case'])))
                                thumb256_path = os.path.abspath(
                                    os.path.join(path, test[img_key].replace(test['test_case'],
                                                                             'thumb256_' + test['test_case'])))

                                if os.path.exists(thumb64_path) and os.path.exists(thumb256_path):
                                    test.update({'thumb64_' + img_key: os.path.relpath(thumb64_path, path)})
                                    test.update({'thumb256_' + img_key: os.path.relpath(thumb256_path, path)})
                                    continue

                                cur_img = Image.open(cur_img_path)
                                thumb64 = cur_img.resize((64, int(64 * cur_img.size[1] / cur_img.size[0])),
                                                         Image.ANTIALIAS)
                                thumb256 = cur_img.resize((256, int(256 * cur_img.size[1] / cur_img.size[0])),
                                                          Image.ANTIALIAS)

                                thumb64.save(thumb64_path, quality=75)
                                thumb256.save(thumb256_path, quality=75)
                            except Exception as err:
                                print("Thumbnail didn't created: json_report - {}, test - {}, img_key - {}".format(json_report, test, img_key))
                                main_logger.error("Thumbnail didn't created: {}".format(str(err)))
                            else:
                                test.update({'thumb64_' + img_key: os.path.relpath(thumb64_path, path)})
                                test.update({'thumb256_' + img_key: os.path.relpath(thumb256_path, path)})

                with open(os.path.join(path, TEST_REPORT_NAME_COMPARED), 'w') as file:
                    json.dump(current_test_report, file, indent=4)
                    main_logger.info("Thumbnails created for: {}".format(os.path.join(path, TEST_REPORT_NAME_COMPARED)))


def build_session_report(report, session_dir):
    total = {'total': 0, 'passed': 0, 'failed': 0, 'error': 0, 'skipped': 0, 'duration': 0, 'render_duration': 0, 'synchronization_duration': 0}

    generate_thumbnails(session_dir)

    current_test_report = {}
    for result in report['results']:
        for item in report['results'][result]:
            try:
                # get report_compare.json by one tests group
                with open(os.path.join(session_dir, report['results'][result][item]['result_path'], TEST_REPORT_NAME_COMPARED), 'r') as file:
                    current_test_report = json.loads(file.read())
            except Exception as err:
                print("Excepted 'report_compare.json' not found for {} {}".format(result, item))
                main_logger.error("Expected 'report_compare.json' not found: {}".format(str(err)))
                report['results'][result][item].update({'render_results': {}})
                report['results'][result][item].update({'render_duration': -0.0})
            else:
                render_duration = 0.0
                synchronization_duration = 0.0
                try:
                    for jtem in current_test_report:
                        for group_report_file in REPORT_FILES:
                            if group_report_file in jtem.keys():
                                # update paths
                                cur_img_path = os.path.abspath(os.path.join(session_dir, report['results'][result][item]['result_path'], jtem[group_report_file]))

                                jtem.update({group_report_file: os.path.relpath(cur_img_path, session_dir)})

                        render_duration += jtem['render_time']
                        synchronization_duration += jtem.get('sync_time', 0.0)
                        if jtem['test_status'] == 'undefined':
                            report['results'][result][item]['total'] += 1
                        else:
                            report['results'][result][item][jtem['test_status']] += 1

                    try:
                        report['machine_info'].update({'render_device': jtem['render_device']})
                        if jtem['tool']:
                            report['machine_info'].update({'tool': jtem['tool']})
                        if report_type != 'ec':
                            report['machine_info'].update({'render_version': jtem['render_version']})
                        else:
                            report['machine_info'].update({'minor_version': jtem['minor_version']})
                        report['machine_info'].update({'core_version': jtem['core_version']})
                    except Exception as err:
                        print("Exception while updating machine_info in session_report")
                        main_logger.warning(str(err))

                    report['results'][result][item]['total'] += report['results'][result][item]['passed'] + \
                                                               report['results'][result][item]['failed'] + \
                                                               report['results'][result][item]['skipped'] + \
                                                               report['results'][result][item]['error']
                    # unite launcher report and render report
                except Exception as err:
                    traceback.print_exc()
                    main_logger.error('Exception while update render report {}'.format(str(err)))
                    render_duration = -0.0

                if current_test_report:
                    report['results'][result][item].update({'render_results': current_test_report})

                report['results'][result][item].update({'render_duration': render_duration})
                report['results'][result][item].update({'synchronization_duration': synchronization_duration})

    # get summary results
    for result in report['results']:
        for item in report['results'][result]:
            for key in total:
                total[key] += report['results'][result][item][key]
    report.update({'summary': total})
    report['machine_info'].update({'reporting_date': datetime.date.today().strftime('%m/%d/%Y %H:%M:%S')})

    save_json_report(report, session_dir, SESSION_REPORT)

    return report


def generate_empty_render_result(summary_report, lost_test_package, gpu_os_case, gpu_name, os_name, lost_tests_count, node_retry_info, status):
    summary_report[gpu_os_case]['results'][lost_test_package] = {}
    # add empty conf
    summary_report[gpu_os_case]['results'][lost_test_package][""] = {}
    # specify data
    summary_report[gpu_os_case]['results'][lost_test_package][""]['duration'] = 0.0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['error'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['failed'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['machine_info'] = ""
    summary_report[gpu_os_case]['results'][lost_test_package][""]['passed'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['render_duration'] = -0.0
    summary_report[gpu_os_case]['results'][lost_test_package][""]['render_results'] = []
    summary_report[gpu_os_case]['results'][lost_test_package][""]['result_path'] = ""
    summary_report[gpu_os_case]['results'][lost_test_package][""]['skipped'] = 0
    summary_report[gpu_os_case]['results'][lost_test_package][""][status] = lost_tests_count
    summary_report[gpu_os_case]['results'][lost_test_package][""]['total'] = lost_tests_count

    host_name = ''
    for retry_info in node_retry_info:
        try:
            retry_gpu_name = PLATFORM_CONVERTATIONS[retry_info['osName']]["cards"][retry_info['gpuName']]
            retry_os_name = PLATFORM_CONVERTATIONS[retry_info['osName']]["os_name"]
            if retry_gpu_name in gpu_os_case and retry_os_name in gpu_os_case:
                for groups in retry_info['Tries']:
                    package_or_default_execution = None
                    for group in groups.keys():
                        parsed_group_name = group.split('~')[0]
                        #all non splitTestsExecution and non regression builds (e.g. any build of core)
                        if 'DefaultExecution' in group:
                            package_or_default_execution = group
                            break
                        elif parsed_group_name.endswith('.json') and lost_test_package not in group.split('~')[1]:
                            with open(os.path.abspath(os.path.join('..', 'jobs', parsed_group_name))) as f:
                                if lost_test_package in json.load(f)['groups']:
                                    package_or_default_execution = group
                                    break
                    if lost_test_package in groups.keys() or package_or_default_execution:
                        for test_tries in retry_info['Tries']:
                            if lost_test_package in test_tries:
                                host_name = groups[lost_test_package][-1]['host']
                                break
                        if not host_name and package_or_default_execution:
                            host_name = groups[package_or_default_execution][-1]['host']
        except Exception as e:
            print("Failed to process retry info. Reason: {}".format(str(e)))

    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info'] = {}

    if host_name:
        # replace tester prefix
        host_name = host_name.replace('PC-TESTER-', '').replace('PC-RENDERER-', '')
        # replace OSX postfix
        host_name = host_name.replace('-OSX', '')
        # Ubuntu1804 -> Ubuntu18
        host_name = host_name.replace('1804', '18')
        # capitalize only first letter of each word of host name
        host_name_parts = host_name.split('-')
        processed_host_name_parts = []
        for part in host_name_parts:
            processed_host_name_parts.append(part.capitalize())
        host_name = '-'.join(processed_host_name_parts)

        # Windows -> WIN10
        host_name = host_name.replace('Windows', 'WIN10')
    else:
        if status == 'skipped':
            host_name = 'Skipped'
        else:
            host_name = 'Unknown'

    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info']['host'] = host_name
    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info']['os'] = os_name
    summary_report[gpu_os_case]['results'][lost_test_package][""]['recovered_info']['render_device'] = gpu_name

    summary_report[gpu_os_case]['summary'][status] += lost_tests_count
    summary_report[gpu_os_case]['summary']['total'] += lost_tests_count


def build_summary_report(work_dir, node_retry_info, collect_tracked_metrics):
    rc = 0
    summary_report = {}
    common_info = {}
    tracked_metrics_data = {}
    for path, dirs, files in os.walk(os.path.abspath(work_dir)):
        for file in files:
            # build summary report
            if file.endswith(SESSION_REPORT):
                basepath = os.path.relpath(path, work_dir)
                with open(os.path.join(path, file), 'r') as report_file:
                    temp_report = json.loads(report_file.read())
                    try:
                        basename = temp_report['machine_info']['render_device'] + ' ' + temp_report['machine_info']['os']
                    except KeyError:
                        continue

                    # update relative paths
                    try:
                        for test_package in temp_report['results']:
                            for test_conf in temp_report['results'][test_package]:
                                temp_report['results'][test_package][test_conf].update(
                                    {'machine_info': temp_report['machine_info']})

                                if common_info:
                                    for key in common_info:
                                        if not temp_report['machine_info'][key] in common_info[key]:
                                            if key == 'reporting_date':
                                                if common_info.get(key, [''])[0] > temp_report['machine_info'][key]:
                                                    common_info[key] = [temp_report['machine_info'][key]]
                                            elif key == 'render_version' and temp_report['machine_info'][key]:
                                                common_info[key].append(temp_report['machine_info'][key])
                                                if len(common_info[key]) > 1:
                                                    rc = -5
                                            else:
                                                common_info[key].append(temp_report['machine_info'][key])
                                else:
                                    common_info.update({'reporting_date': [temp_report['machine_info']['reporting_date']]})

                                    if report_type != 'ec':
                                        if temp_report['machine_info']['render_version']:
                                            common_info.update({'render_version': [temp_report['machine_info']['render_version']]})
                                        else:
                                            common_info.update({'render_version': []})
                                    else:
                                        common_info.update({'minor_version': [temp_report['machine_info']['minor_version']]})
                                    common_info.update({'core_version': [temp_report['machine_info']['core_version']]})

                                for jtem in temp_report['results'][test_package][test_conf]['render_results']:
                                    for group_report_file in REPORT_FILES:
                                        if group_report_file in jtem.keys():
                                            jtem.update({group_report_file: os.path.relpath(os.path.join(work_dir, basepath, jtem[group_report_file]), work_dir)})

                                    # collect tracked metrics for test cases
                                    if collect_tracked_metrics:
                                        for tracked_metric in tracked_metrics:
                                            if tracked_metric in jtem:
                                                test_case = jtem['test_case']
                                                if basename not in tracked_metrics_data:
                                                    tracked_metrics_data[basename] = {}
                                                    tracked_metrics_data[basename]['groups'] = {}
                                                groups = tracked_metrics_data[basename]['groups']
                                                if test_package not in groups:
                                                    groups[test_package] = {}
                                                    groups[test_package]['metrics'] = {}
                                                if test_case not in groups[test_package]['metrics']:
                                                    groups[test_package]['metrics'][test_case] = {}
                                                groups[test_package]['metrics'][test_case][tracked_metric] = jtem[tracked_metric]

                                    for message in jtem.get('message', []):
                                        if 'Unacceptable time difference' in message:
                                            main_logger.error(test_package)
                                            temp_report['results'][test_package][test_conf].update(
                                                {'status': GROUP_TIMEOUT})

                                temp_report['results'][test_package][test_conf].update(
                                    {'result_path': os.path.relpath(
                                        os.path.join(work_dir, basepath, temp_report['results'][test_package][test_conf]['result_path']),
                                        work_dir)}
                                )

                            # aggregate tracked metrics for test groups
                            if collect_tracked_metrics and basename in tracked_metrics_data and test_package in tracked_metrics_data[basename]['groups']:
                                tracked_metrics_summary = {}
                                for tracked_metric in tracked_metrics:
                                    groups = tracked_metrics_data[basename]['groups']
                                    metric_summary = 0
                                    number = 0
                                    for test_case in groups[test_package]['metrics']:
                                        if tracked_metric in groups[test_package]['metrics'][test_case]:
                                            metric_summary += groups[test_package]['metrics'][test_case][tracked_metric]
                                            number +=1
                                    if number:
                                        if tracked_metrics[tracked_metric]['function'] == 'avrg':
                                            tracked_metrics_summary[tracked_metric] = metric_summary / number
                                        else:
                                            tracked_metrics_summary[tracked_metric] = metric_summary
                                groups[test_package]['summary'] = tracked_metrics_summary
                    except Exception as err:
                        traceback.print_exc()
                        main_logger.error("Processing of {} has produced error: {}".format(basepath.split(os.path.sep)[-1], str(err)))

                    if basename in summary_report.keys():
                        summary_report[basename]['results'].update(temp_report['results'])
                        for key in temp_report['summary'].keys():
                            summary_report[basename]['summary'][key] += temp_report['summary'][key]
                    else:
                        summary_report[basename] = {}
                        summary_report[basename].update({'results': temp_report['results']})
                        summary_report[basename].update({'summary': temp_report['summary']})

    # aggregate tracked metrics for platforms
    if collect_tracked_metrics:
        for platform in tracked_metrics_data:
            tracked_metrics_summary = {}
            for tracked_metric in tracked_metrics:
                groups = tracked_metrics_data[platform]['groups']
                metric_summary = 0
                number = 0
                for test_group in groups:
                    if tracked_metric in groups[test_group]['summary']:
                        metric_summary += groups[test_group]['summary'][tracked_metric]
                        number +=1
                if number:
                    if tracked_metrics[tracked_metric]['function'] == 'avrg':
                        tracked_metrics_summary[tracked_metric] = metric_summary / number
                    else:
                        tracked_metrics_summary[tracked_metric] = metric_summary
            tracked_metrics_data[platform]['summary'] = tracked_metrics_summary

    for key in common_info:
        common_info[key] = ' '.join(str(x) for x in common_info[key])

    missing_tests_jsons = {'error': os.path.join(work_dir, LOST_TESTS_JSON_NAME)}
    if show_skipped_groups:
        missing_tests_jsons['skipped'] = os.path.join(work_dir, SKIPPED_TESTS_JSON_NAME)
    for key in missing_tests_jsons:
        missing_tests_json = missing_tests_jsons[key]
        if os.path.exists(missing_tests_json):
            with open(os.path.join(missing_tests_json), "r") as file:
                lost_tests_count = json.load(file)
            for lost_test_result in lost_tests_count:
                test_case_found = False
                gpu_name = lost_test_result.split('-')[0]
                os_name = lost_test_result.split('-')[1]
                for gpu_os_case in summary_report:
                    if gpu_name.lower() in gpu_os_case.lower() and os_name.lower() in gpu_os_case.lower():
                        for lost_test_package in lost_tests_count[lost_test_result]:
                            generate_empty_render_result(summary_report, lost_test_package, gpu_os_case, gpu_name, os_name, lost_tests_count[lost_test_result][lost_test_package], node_retry_info, key)
                        test_case_found = True
                        break
                # if all data for GPU + OS was lost (it can be regression.json execution)
                if not test_case_found:
                    gpu_os_case = lost_test_result.replace('-', ' ')
                    summary_report[gpu_os_case] = {}
                    summary_report[gpu_os_case]['results'] = {}
                    summary_report[gpu_os_case]['summary'] = {}
                    summary_report[gpu_os_case]['summary']['duration'] = 0.0
                    summary_report[gpu_os_case]['summary']['error'] = 0
                    summary_report[gpu_os_case]['summary']['failed'] = 0
                    summary_report[gpu_os_case]['summary']['passed'] = 0
                    summary_report[gpu_os_case]['summary']['render_duration'] = -0.0
                    summary_report[gpu_os_case]['summary']['skipped'] = 0
                    summary_report[gpu_os_case]['summary']['total'] = 0
                    for lost_test_package in lost_tests_count[lost_test_result]:
                        generate_empty_render_result(summary_report, lost_test_package, gpu_os_case, gpu_name, os_name, lost_tests_count[lost_test_result][lost_test_package], node_retry_info, key)

    for config in summary_report:
        summary_report[config]['summary']['setup_duration'] = summary_report[config]['summary']['duration'] - summary_report[config]['summary']['render_duration'] - summary_report[config]['summary'].get('synchronization_duration', -0.0)
        for test_package in summary_report[config]['results']:
            summary_report[config]['results'][test_package]['']['setup_duration'] = summary_report[config]['results'][test_package]['']['duration'] - summary_report[config]['results'][test_package]['']['render_duration'] - summary_report[config]['results'][test_package][''].get('synchronization_duration', -0.0)

    return summary_report, common_info, tracked_metrics_data, rc


def build_performance_report(summary_report, major_title):
    performance_report = AutoDict()
    performance_report_detail = AutoDict()
    hardware = {}
    render_info = []

    for key in summary_report:
        platform = summary_report[key]
        for group in platform['results']:
            if 'results' not in platform:
                break

            conf = list(platform['results'][group].keys())[0]

            if platform['results'][group][conf]['machine_info'] == "":
                # if machine info is empty it's blank data for lost test cases
                continue

            temp_report = platform['results'][group][conf]
            tool = temp_report['machine_info'].get('tool', major_title)

            hw = platform['results'][group][conf]['machine_info']['render_device'] + ' ' + platform['results'][group][conf]['machine_info']['os'].split()[0]
            render_info.append([tool, hw, platform['summary']['render_duration'], platform['summary'].get('synchronization_duration', -0.0)])
            if hw not in hardware:
                hardware[hw] = platform['summary']['render_duration']

            results = platform.pop('results', None)
            info = temp_report
            for test_package in results:
                for test_config in results[test_package]:
                    results[test_package][test_config].pop('render_results', None)

            performance_report[tool].update({hw: info})

            for test_package in results:
                for test_config in results[test_package]:
                    test_info = {'render': results[test_package][test_config]['render_duration'], 'sync': results[test_package][test_config].get('synchronization_duration', -0.0), 'total': results[test_package][test_config]['duration']}
                    performance_report_detail[test_package].update(
                        {hw: test_info})

    tools = set([tool for tool, device, render, sync in render_info])
    devices = set([device for tool, device, render, sync in render_info])
    summary_info_for_report = {t: {device: {} for device in devices} for t in tools}

    tools_count = {}
    for tool in tools:
        for t, d, r, s in render_info:
            if t == tool:
                tools_count[tool] = tools_count.get(tool, 0) + 1
    for t, d, r, s in render_info:
        summary_info_for_report[max(tools_count.items(), key=operator.itemgetter(1))[0]]['actual'] = True

    for tool, device, render, sync in render_info:
        summary_info_for_report[tool][device]['render'] = render
        summary_info_for_report[tool][device]['sync'] = sync

    for tool in tools:
        for device in devices:
            if not 'render' in summary_info_for_report[tool][device]:
                summary_info_for_report[tool][device]['render'] = -0.0
                summary_info_for_report[tool][device]['sync'] = -0.0

    hardware = sorted(hardware.items(), key=operator.itemgetter(1))
    return performance_report, hardware, performance_report_detail, summary_info_for_report


def build_compare_report(summary_report):
    compare_report = AutoDict()
    hardware = []
    for platform in summary_report.keys():
        for test_package in summary_report[platform]['results']:
            for test_config in summary_report[platform]['results'][test_package]:
                temp_report = summary_report[platform]['results'][test_package][test_config]

                if temp_report['machine_info'] == "":
                    # if machine info is empty it's blank data for lost test cases
                    continue

                # force add gpu from baseline
                hw = temp_report['machine_info']['render_device'] + ' ' + temp_report['machine_info']['os'].split()[0]
                hw_bsln = temp_report['machine_info']['render_device'] + " [Baseline]"

                if hw not in hardware:
                    hardware.append(hw)
                    hardware.append(hw_bsln)

                # collect images links
                for item in temp_report['render_results']:
                    # if test is processing first time
                    if not compare_report[item['test_case']]:
                        compare_report[item['test_case']] = {}

                    try:
                        for img_key in POSSIBLE_JSON_IMG_RENDERED_KEYS + POSSIBLE_JSON_IMG_RENDERED_KEYS_THUMBNAIL:
                            if img_key in item.keys():
                                compare_report[item['test_case']].update({hw: item[img_key]})
                        for img_key in POSSIBLE_JSON_IMG_BASELINE_KEYS + POSSIBLE_JSON_IMG_BASELINE_KEYS_THUMBNAIL:
                            if img_key in item.keys():
                                compare_report[item['test_case']].update({hw_bsln: item[img_key]})
                    except KeyError as err:
                        print("Missed testcase detected: platform - {}, test_package - {}, test_config - {}, item - {}".format(platform, test_package, test_config, item))
                        main_logger.error("Missed testcase detected {}".format(str(err)))

    return compare_report, hardware


def build_local_reports(work_dir, summary_report, common_info, jinja_env, tracked_metrics, tracked_metrics_history):
    work_dir = os.path.abspath(work_dir)

    template = jinja_env.get_template('local_template.html')
    report_dir = ""

    try:
        for execution in summary_report:
            for test in summary_report[execution]['results']:
                for config in summary_report[execution]['results'][test]:
                    report_dir = summary_report[execution]['results'][test][config]['result_path']

                    render_report = []

                    if os.path.exists(os.path.join(work_dir, report_dir, TEST_REPORT_NAME_COMPARED)):
                        with open(os.path.join(work_dir, report_dir, TEST_REPORT_NAME_COMPARED), 'r') as file:
                            render_report = json.loads(file.read())
                            keys_for_upd = ['tool', 'render_device', 'testing_start', 'test_group']
                            for key_upd in keys_for_upd:
                                if key_upd in render_report[0].keys():
                                    common_info.update({key_upd: render_report[0][key_upd]})
                    else:
                        # test case was lost
                        continue

                    # for core baseline_render_time initialize via compareByJson script
                    if report_type != 'ec':
                        baseline_report_path = os.path.abspath(os.path.join(work_dir, execution, 'Baseline', test, BASELINE_REPORT_NAME))
                        baseline_report = []

                        if os.path.exists(baseline_report_path):
                            with open(baseline_report_path, 'r') as file:
                                baseline_report = json.loads(file.read())
                                for render_item in render_report:
                                    try:
                                        baseline_item = list(filter(lambda item: item['test_case'] == render_item['test_case'], baseline_report))[0]
                                        render_item.update({'baseline_render_time': baseline_item['render_time']})
                                    except IndexError:
                                        pass

                    # choose right plugin version based on building report type
                    if report_type != 'ec':
                        version_in_title = common_info['render_version']
                    else:
                        version_in_title = common_info['core_version']
                    html = template.render(title="{} {} plugin version: {}".format(common_info['tool'], test, version_in_title),
                                           common_info=common_info,
                                           render_report=render_report,
                                           pre_path=os.path.relpath(work_dir, os.path.join(work_dir, report_dir)),
                                           platform=execution,
                                           tracked_metrics=tracked_metrics,
                                           tracked_metrics_history=tracked_metrics_history)
                    save_html_report(html, os.path.join(work_dir, report_dir), 'report.html', replace_pathsep=True)
    except Exception as err:
        traceback.print_exc()
        main_logger.error(str(err))


# Expected error return codes
# -1 - Summary report can't be built
# -2 - Performance report can't be built
# -3 - Compare report can't be built
# -4 - Local reports can't be built
# -5 - More than one plugin versions
def build_summary_reports(work_dir, major_title, commit_sha='undefined', branch_name='undefined', commit_message='undefined', engine='', build_number=''):
    rc = 0

    if '' in engine:
        engine = None

    if os.path.exists(os.path.join(work_dir, 'report_resources')):
        rmtree(os.path.join(work_dir, 'report_resources'), True)

    try:
        copytree(os.path.join(os.path.split(__file__)[0], REPORT_RESOURCES_PATH),
                 os.path.join(work_dir, 'report_resources'))
    except Exception as err:
        main_logger.error("Failed to copy report resources: {}".format(str(err)))

    env = jinja2.Environment(
        loader=jinja2.PackageLoader('core.reportExporter', 'templates'),
        autoescape=True
    )
    # check that original_render variable exists
    if not 'original_render' in globals():
        global original_render
        original_render = ''
    env.globals.update({'original_render': original_render,
                        'report_type': report_type,
                        'pre_path': '.',
                        'config': config})
    env.filters['env_override'] = env_override
    env.filters['get_jobs_launcher_version'] = get_jobs_launcher_version

    common_info = {}
    summary_report = None

    if os.path.exists(os.path.join(work_dir, RETRY_INFO_NAME)):
        with open(os.path.join(work_dir, RETRY_INFO_NAME), "r") as file:
            node_retry_info = json.load(file)
    else:
        node_retry_info = []

    main_logger.info("Saving summary report...")

    try:
        summary_template = env.get_template('summary_template.html')
        detailed_summary_template = env.get_template('detailed_summary_template.html')

        summary_report, common_info, tracked_metrics_data, rc = build_summary_report(work_dir, node_retry_info, bool(build_number))

        add_retry_info(summary_report, node_retry_info, work_dir)

        common_info.update({'commit_sha': commit_sha})
        common_info.update({'branch_name': branch_name})
        common_info.update({'commit_message': commit_message})
        common_info.update({'engine': engine})
        save_json_report(summary_report, work_dir, SUMMARY_REPORT)
        tracked_metrics_history = OrderedDict()
        if build_number:
            try:
                tracked_metrics_file_path = os.path.join(work_dir, TRACKED_METRICS_LOCATION_NAME)
                if not os.path.exists(tracked_metrics_file_path):
                    os.makedirs(tracked_metrics_file_path)
                save_json_report(tracked_metrics_data, tracked_metrics_file_path, TRACKED_METRICS_JSON_NAME.format(build_number))
            except Exception as e:
                main_logger.error("Can't save tracked metrics data: {}".format(str(e)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
            try:
                tracked_metrics_files = sorted(glob(os.path.join(tracked_metrics_file_path ,'*.json')), key=lambda x: int(os.path.splitext(x)[0].split('_')[-1]), reverse=True)
                for i in range(tracked_metrics_files_number):
                    if i == len(tracked_metrics_files):
                        break
                    with open(tracked_metrics_files[i], 'r') as tracked_metrics_file:
                        tracked_metrics_file_data = json.load(tracked_metrics_file) 
                    file_build_number = re.search(r'\d+', tracked_metrics_files[i].split(os.path.sep)[-1]).group(0)
                    tracked_metrics_history[file_build_number] = tracked_metrics_file_data
                tracked_metrics_history = OrderedDict(reversed(list(tracked_metrics_history.items())))
            except Exception as e:
                main_logger.error("Can't collect history of tracked metrics: {}".format(str(e)))
                main_logger.error("Traceback: {}".format(traceback.format_exc()))
        summary_html = summary_template.render(title=major_title + " Summary",
                                               report=summary_report,
                                               pageID="summaryA",
                                               PIX_DIFF_MAX=PIX_DIFF_MAX,
                                               common_info=common_info,
                                               synchronization_time=sync_time(summary_report),
                                               tracked_metrics=tracked_metrics,
                                               tracked_metrics_history=tracked_metrics_history)
        save_html_report(summary_html, work_dir, SUMMARY_REPORT_HTML, replace_pathsep=True)

        for execution in summary_report.keys():
            detailed_summary_html = detailed_summary_template.render(title=major_title + " " + execution,
                                                                     report=summary_report,
                                                                     pageID="summaryA",
                                                                     PIX_DIFF_MAX=PIX_DIFF_MAX,
                                                                     common_info=common_info,
                                                                     i=execution)
            save_html_report(detailed_summary_html, work_dir, execution + "_detailed.html", replace_pathsep=True)
    except Exception as err:
        try:
            traceback.print_exc()
            main_logger.error(summary_html)
            save_html_report("Error while building summary report: {}".format(str(err)), work_dir, SUMMARY_REPORT_HTML,
                             replace_pathsep=True)
        except Exception as err:
            traceback.print_exc()
        rc = -1

    main_logger.info("Saving performance report...")
    try:
        setup_time_count(work_dir)
        copy_summary_report = copy.deepcopy(summary_report)
        performance_template = env.get_template('performance_template.html')

        performance_report, hardware, performance_report_detail, summary_info_for_report = build_performance_report(copy_summary_report, major_title)

        setup_sum, setup_details = setup_time_report(work_dir, performance_report_detail)

        save_json_report(performance_report, work_dir, PERFORMANCE_REPORT)
        save_json_report(performance_report_detail, work_dir, 'performance_report_detailed.json')
        performance_html = performance_template.render(title=major_title + " Performance",
                                                       performance_report=performance_report,
                                                       hardware=hardware,
                                                       performance_report_detail=performance_report_detail,
                                                       pageID="performanceA",
                                                       common_info=common_info,
                                                       test_info=summary_info_for_report,
                                                       setupTimeSum=setup_sum,
                                                       setupTimeDetails=setup_details,
                                                       synchronization_time=sync_time(summary_report))
        save_html_report(performance_html, work_dir, PERFORMANCE_REPORT_HTML, replace_pathsep=True)
    except Exception as err:
        try:
            traceback.print_exc()
            main_logger.error(performance_html)
            save_html_report(performance_html, work_dir, PERFORMANCE_REPORT_HTML, replace_pathsep=True)
        except Exception as err:
            traceback.print_exc()
        # TODO: make building of performance tab more stable
        # rc = -2

    main_logger.info("Saving compare report...")
    try:
        compare_template = env.get_template('compare_template.html')
        copy_summary_report = copy.deepcopy(summary_report)

        compare_report, hardware = build_compare_report(copy_summary_report)

        save_json_report(compare_report, work_dir, COMPARE_REPORT)
        compare_html = compare_template.render(title=major_title + " Compare",
                                               hardware=hardware,
                                               compare_report=compare_report,
                                               pageID="compareA",
                                               common_info=common_info)
        save_html_report(compare_html, work_dir, COMPARE_REPORT_HTML, replace_pathsep=True)
    except Exception as err:
        try:
            traceback.print_exc()
            main_logger.error(compare_html)
            save_html_report(compare_html, work_dir, "compare_report.html", replace_pathsep=True)
        except Exception as err:
            traceback.print_exc()
        rc = -3

    try:
        build_local_reports(work_dir, summary_report, common_info, env, tracked_metrics, tracked_metrics_history)
    except Exception as err:
        traceback.print_exc()
        main_logger.error(str(err))
        rc = -4

    exit(rc)


def setup_time_report(work_dir, report):
    setup_sum_list = config.SETUP_STEPS_RPR_PLUGIN
    setup_steps_dict = {}
    for step in setup_sum_list:
        setup_steps_dict[step] = -0.0
    setup_sum = {}

    try:
        with open(os.path.abspath(os.path.join(work_dir, 'setup_time.json'))) as f:
            setup_details = json.load(f)
    except:
        main_logger.error("Can't open setup_time.json")
        return (None, None)

    setup_sum['Summary'] = {}

    if setup_details.keys():
        for conf in setup_details.keys():
            setup_sum[conf] = setup_steps_dict.copy()
            for group in setup_details[conf]:
                sum_steps = 0
                for key in list(set().union(setup_sum_list, setup_details[conf][group].keys())):
                    setup_details[conf][group][key] = round(setup_details[conf][group].get(key, -0.0), 3) # jinja don't want to round these data
                    setup_sum[conf][key] = round(setup_sum[conf].get(key, -0.0) + setup_details[conf][group][key], 3)

                    sum_steps += setup_details[conf][group][key]

                setup_details[conf][group]['Refactor logs'] = round(report[group][conf]['total'] - sum_steps - report[group][conf]['render'] - report[group][conf]['sync'], 3)
                setup_sum[conf]['Refactor logs'] = round(setup_sum[conf].get('Refactor logs', -0.0) + setup_details[conf][group]['Refactor logs'], 3)
            setup_sum['Summary'][conf] = 0.0
            for step in setup_sum[conf]:
                setup_sum['Summary'][conf] += setup_sum[conf][step]
        setup_sum['steps'] = list(set().union(setup_sum_list, setup_details[conf][group].keys()))

    return setup_sum, setup_details


def sync_time(summary_report):
    try:
        if sum(summary_report[config]['summary'].get('synchronization_duration', -0.0) for config in summary_report) > 0:
            for config in summary_report:
                if 'synchronization_duration' in summary_report[config]['summary']:
                    summary_report[config]['summary']['duration_sync'] = summary_report[config]['summary'].get('synchronization_duration', -0.0) + summary_report[config]['summary']['render_duration']
                    for test_package in summary_report[config]['results']:
                        summary_report[config]['results'][test_package]['']['duration_sync'] = summary_report[config]['results'][test_package][''].get('synchronization_duration', -0.0) + summary_report[config]['results'][test_package]['']['render_duration']
        else:
            for config in summary_report:
                summary_report[config]['summary']['duration_sync'] = summary_report[config]['summary']['render_duration']
                for test_package in summary_report[config]['results']:
                    summary_report[config]['results'][test_package]['']['duration_sync'] = summary_report[config]['results'][test_package]['']['render_duration']
            raise Exception('Some "synchronization_time" is 0')
    except Exception as e:
        main_logger.error(str(e))
        return False
    return True


def setup_time_count(work_dir):
    performance_list = {}
    for root, subdirs, files in os.walk(work_dir):
        performance_jsons = [os.path.join(root, f) for f in files if f.endswith('_performance.json')]
        for perf_json in performance_jsons:
            try:
                perf_list = json.load(open(perf_json))
                summ_perf = {}
                for event in perf_list:
                    if summ_perf.get(event['name'], ''):
                        summ_perf[event['name']] += event['time']
                    else:
                        summ_perf[event['name']] = event['time']

                group = os.path.split(perf_json)[1].rpartition('_')[0]
                pcConfig = 'undefined'
                render_json = next(iter([os.path.join(root, tmp) for tmp in files if tmp.endswith(config.SESSION_REPORT)]), '')
                if os.path.exists(render_json):
                    with open(render_json) as rpr_json_file:
                        rpr_json = json.load(rpr_json_file)
                        pcConfig = rpr_json['machine_info']['render_device'] + ' ' + rpr_json['machine_info']['os'].split()[0]
                if pcConfig not in performance_list.keys():
                    performance_list[pcConfig] = {}
                performance_list[pcConfig][group] = summ_perf
            except Exception as err:
                main_logger.error('Error while setup time steps occurred "{}"'.format(str(err)))
    with open(os.path.join(work_dir, 'setup_time.json'), 'w') as f:
        f.write(json.dumps(performance_list, indent=4))


def add_retry_info(summary_report, retry_info, work_dir):
    try:
        for config in summary_report:
            for test_package in summary_report[config]['results']:
                if summary_report[config]['results'][test_package]['']['machine_info']:
                    node = summary_report[config]['results'][test_package]['']['machine_info']['host']
                else:
                    node = summary_report[config]['results'][test_package]['']['recovered_info']['host']
                for retry in retry_info:
                    for tester in retry['Testers']:
                        if str(node).upper() in tester:
                            for groups in retry['Tries']:
                                package_or_default_execution = None
                                for group in groups.keys():
                                    parsed_group_name = group.split('~')[0]
                                    #all non splitTestsExecution and non regression builds (e.g. any build of core)
                                    if 'DefaultExecution' in group:
                                        package_or_default_execution = group
                                        break
                                    elif parsed_group_name.endswith('.json') and test_package not in group.split('~')[1]:
                                        with open(os.path.abspath(os.path.join('..', 'jobs', parsed_group_name))) as f:
                                            if test_package in json.load(f)['groups']:
                                                package_or_default_execution = group
                                                break
                                if test_package in groups.keys() or package_or_default_execution:
                                    retries_list = []
                                    groupOrJson = []
                                    for test_tries in retry['Tries']:
                                        if test_package in test_tries:
                                            groupOrJson = test_tries[test_package]
                                            break
                                    if not groupOrJson and package_or_default_execution:
                                        groupOrJson = test_tries[package_or_default_execution]
                                    if groupOrJson:
                                        for test_try in groupOrJson:
                                            retries_list.append(test_try)

                                        for test_try in retries_list:
                                            if not os.path.exists(os.path.join(work_dir, test_try['link'])):
                                                test_try['link'] = ''

                                        summary_report[config]['results'][test_package]['']['retries'] = retries_list
    except Exception as e:
        main_logger.error(
            'Error "{}" while adding retry info'.format(str(e)))
