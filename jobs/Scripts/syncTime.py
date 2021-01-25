import argparse
import os
import json
import cpuinfo
import sys
import re
sys.path.append(os.path.abspath(os.path.join(
	os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
import jobs_launcher.core.performance_counter as perf_count
import jobs_launcher.core.config as core_config


def sync_time(directory):
    perf_count.event_record(directory, 'Sync time count', True)
    files = [f for f in os.listdir(
        directory) if os.path.isfile(os.path.join(directory, f))if 'renderTool' in f]

    logs = ''

    for f in files:
        with open(os.path.realpath(os.path.join(directory, f))) as log:
            logs += log.read()

    log_path = ''
    case_report_name = ''
    case_report_path = ''
    for line in logs.splitlines():
        if [l for l in ['Save report', 'Create log'] if l in line]:
            test_case = line.split().pop()
            case_report_name = test_case + core_config.CASE_REPORT_SUFFIX
            case_report_path = os.path.join(directory, case_report_name)
            log_path = os.path.join(directory, 'render_tool_logs', test_case + '.log')

        if os.path.exists(log_path):
            with open(log_path, 'a') as case_log:
                case_log.write(line + '\n')

        if os.path.exists(case_report_path):
            with open(case_report_path, 'r') as case_report:
                case_json = json.load(case_report)

            sync_minutes = re.findall(
                'Scene synchronization time: (\d*)m', line)
            sync_seconds = re.findall(
                'Scene synchronization time: .*?(\d*)s', line)
            sync_milisec = re.findall(
                'Scene synchronization time: .*?(\d*)ms', line)

            sync_minutes = float(next(iter(sync_minutes or []), 0))
            sync_seconds = float(next(iter(sync_seconds or []), 0))
            sync_milisec = float(next(iter(sync_milisec or []), 0))

            synchronization_time = sync_minutes * 60 + sync_seconds + sync_milisec / 1000
            case_json[0]['sync_time'] += synchronization_time
            if case_json[0]['render_time'] != 0:
                case_json[0]['render_time'] -= synchronization_time

            with open(case_report_path, 'w') as case_report:
                case_report.write(json.dumps(case_json, indent=4))
    perf_count.event_record(directory, 'Sync time count', False)

    files = os.listdir(directory)
    json_files = list(filter(lambda x: x.endswith('RPR.json'), files))
    cpu_name = cpuinfo.get_cpu_info()['brand']
    for f in range(len(json_files)):
        with open(os.path.join(directory, json_files[f]), 'r') as w:
            json_report = w.read()
        json_report = json_report.replace("CPU0", cpu_name)
        json_report = json.loads(json_report)
        with open(os.path.join(directory, json_files[f]), 'w') as file:
            json.dump(json_report, file, indent=' ')

    cpu_name = cpuinfo.get_cpu_info()['brand']


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--work_dir', required=True)
    args = parser.parse_args()
    sync_time(args.work_dir)
