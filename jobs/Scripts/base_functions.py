import bpy
import addon_utils
import datetime
import time
import json
import re
import os.path as path
import os
import sys
import glob
from shutil import copyfile

WORK_DIR = r'{work_dir}'
TEST_TYPE = '{testType}'
RES_PATH = r'{res_path}'
RESOLUTION_X = {resolution_x}
RESOLUTION_Y = {resolution_y}
DELEGATE = r'{delegate}'
RETRIES = {retries}
LOGS_DIR = path.join(WORK_DIR, 'render_tool_logs')


def event(name, start, case):
    pathEvents = path.join(os.path.dirname(os.path.realpath(__file__)), 'events')
    with open(path.join(pathEvents, str(glob.glob(path.join(pathEvents, '*.json')).__len__() + 1) + '.json'), 'w') as f:
        f.write(json.dumps({{'name': name, 'time': datetime.datetime.utcnow().strftime(
            '%d/%m/%Y %H:%M:%S.%f'), 'start': start, 'case': case}}, indent=4))


def logging(message):
    print(' >>> [USD TEST] [' +
          datetime.datetime.now().strftime('%H:%M:%S') + '] ' + message)


def reportToJSON(case, render_time=0):
    # TODO replace suffix by value from config
    path_to_file = path.join(WORK_DIR, case['case'] + '_RPR.json')

    with open(path_to_file, 'r') as file:
        report = json.loads(file.read())[0]

    if case['status'] == 'inprogress':
        report['test_status'] = 'passed'
        report['group_timeout_exceeded'] = False
    else:
        report['test_status'] = case['status']

    logging('Create report json ({{}} {{}})'.format(
            case['case'], report['test_status']))

    if case['status'] == 'error':
        number_of_tries = case.get('number_of_tries', 0)
        if number_of_tries == RETRIES:
            error_message = 'Testcase wasn\'t executed successfully (all attempts were used). Number of tries: {{}}'.format(str(number_of_tries))
        else:
            error_message = 'Testcase wasn\'t executed successfully. Number of tries: {{}}'.format(str(number_of_tries))
        report['message'] = [error_message]
        report['group_timeout_exceeded'] = False
    else:
        report['message'] = []

    report['date_time'] = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    report['render_time'] = render_time
    report['test_group'] = TEST_TYPE
    report['test_case'] = case['case']
    report['case_functions'] = case['functions']
    report['difference_color'] = 0
    report['script_info'] = case['script_info']
    report['scene_name'] = case.get('scene', '')
    if case['status'] != 'skipped':
        report['file_name'] = case['case'] + case.get('extension', '.jpg')
        report['render_color_path'] = path.join('Color', report['file_name'])

    # save metrics which can be received witout call of functions of Blender
    with open(path_to_file, 'w') as file:
        file.write(json.dumps([report], indent=4))

    try:
        report['tool'] = 'Blender ' + bpy.app.version_string.split(' (')[0]
    except Exception as e:
        logging('Failed to get Blender version. Reason: {{}}'.format(str(e)))

    # save metrics which can't be received witout call of functions of Blender (additional measures to avoid stucking of Blender)
    with open(path_to_file, 'w') as file:
        file.write(json.dumps([report], indent=4))


def render_tool_log_path(name):
    return path.join(LOGS_DIR, name + '.log')

# TODO: remove support for deprecated core



def enable_usd(case):
    addon_utils.disable('rprblender')
    event('Load usd', True, case)
    if not addon_utils.check('hdusd')[0]:
        addon_utils.enable('hdusd', default_set=True,
                           persistent=False, handle_error=None)
    set_value(bpy.context.scene.render, 'engine', 'HdUSD')
    event('Load usd', False, case)

    

def set_value(path, name, value):
    if hasattr(path, name):
        setattr(path, name, value)
    else:
        logging('No attribute found ' + name)


def usd_render(case):
    logging('Render image')
    event('Prerender', False, case['case'])
    event('Postrender', True, case['case'])
    start_time = datetime.datetime.now()
    bpy.ops.render.render(write_still=True)
    render_time = (datetime.datetime.now() - start_time).total_seconds()
    event('Postrender', True, case['case'])

    reportToJSON(case, render_time)


def prerender(case):
    logging('Prerender')
    scene = case.get('scene', '')
    scene_name = bpy.path.basename(bpy.context.blend_data.filepath)
    if scene_name != scene:
        try:
            event('Open scene', True, case['case'])
            bpy.ops.wm.open_mainfile(filepath=os.path.join(RES_PATH, scene))
            event('Open scene', False, case['case'])
        except:
            logging("Can't load scene. Exit Blender")
            bpy.ops.wm.quit_blender()

    enable_usd(case['case']) # some cases open scene inside case functions

    event('Prerender', True, case['case'])

    scene = bpy.context.scene

    if RESOLUTION_X and RESOLUTION_Y:
        set_value(scene.render, 'resolution_x', RESOLUTION_X)
        set_value(scene.render, 'resolution_y', RESOLUTION_Y)

    set_value(scene.render.image_settings, 'file_format', 'JPEG')

    bpy.data.scenes["Scene"].hdusd.final.delegate = DELEGATE

    # image settings
    set_value(scene.render.image_settings, 'quality', 100)
    set_value(scene.render.image_settings, 'compression', 0)
    set_value(scene.render.image_settings, 'color_mode', 'RGB')

    # output settings
    set_value(scene.render, 'filepath', os.path.join(WORK_DIR, 'Color', case['case']))
    set_value(scene.render, 'use_placeholder', True)
    set_value(scene.render, 'use_file_extension', True)
    set_value(scene.render, 'use_overwrite', True)

    for function in case['functions']:
        try:
            if re.match('((^\S+|^\S+ \S+) = |^print|^if|^for|^with)', function):
                exec(function)
            else:
                eval(function)
        except Exception as e:
            logging('Error "{{}}" with string "{{}}"'.format(e, function))
    event('Postrender', False, case['case'])


def save_report(case):
    logging('Save report without rendering for ' + case['case'])

    if not os.path.exists(os.path.join(WORK_DIR, 'Color')):
        os.makedirs(os.path.join(WORK_DIR, 'Color'))

    work_dir = path.join(WORK_DIR, 'Color', case['case'] + '.jpg')
    source_dir = path.join(WORK_DIR, '..', '..', '..',
                           '..', 'jobs_launcher', 'common', 'img')

    if case['status'] == 'inprogress':
        copyfile(path.join(source_dir, 'passed.jpg'), work_dir)
    elif case['status'] != 'skipped':
        copyfile(
            path.join(source_dir, case['status'] + '.jpg'), work_dir)

    enable_usd(case['case'])

    reportToJSON(case)


def case_function(case):
    functions = {{
        'prerender': prerender,
        'save_report': save_report
    }}

    func = 'prerender'

    if case['functions'][0] == 'check_test_cases_success_save':
        func = 'save_report'

    if case['status'] == 'fail' or case.get('number_of_tries', 1) == RETRIES:
        case['status'] = 'error'
        func = 'save_report'
    elif case['status'] == 'skipped':
        func = 'save_report'
    else:
        case['number_of_tries'] = case.get('number_of_tries', 0) + 1

    functions[func](case)


# place for extension functions


def main():

    if not os.path.exists(os.path.join(WORK_DIR, LOGS_DIR)):
        os.makedirs(os.path.join(WORK_DIR, LOGS_DIR))

    with open(path.join(WORK_DIR, 'test_cases.json'), 'r') as json_file:
        cases = json.load(json_file)

    event('Open tool', False, next(
        case['case'] for case in cases if case['status'] in ['active', 'fail', 'skipped']))

    total_time = 0

    for case in cases:
        if case['status'] in ['active', 'fail', 'skipped']:
            if case['status'] == 'active':
                case['status'] = 'inprogress'

            with open(path.join(WORK_DIR, 'test_cases.json'), 'w') as file:
                json.dump(cases, file, indent=4)

            log_path = render_tool_log_path(case['case'])
            if not path.exists(log_path):
                with open(log_path, 'w'):
                    logging('Create log file for ' + case['case'])

            logging('In progress: ' + case['case'])

            # TODO replace suffix by value from config
            path_to_file = path.join(WORK_DIR, case['case'] + '_RPR.json')
            with open(path_to_file, 'r') as file:
                report = json.loads(file.read())[0]

            report['render_log'] = path.join('render_tool_logs', case['case'] + '.log')

            with open(path_to_file, 'w') as file:
                file.write(json.dumps([report], indent=4))

            start_time = datetime.datetime.now()
            case_function(case)
            stop_time = (datetime.datetime.now() - start_time).total_seconds()
            case['time_taken'] = stop_time

            if case['status'] == 'inprogress':
                case['status'] = 'done'
                logging(case['case'] + ' done')

            with open(path.join(WORK_DIR, 'test_cases.json'), 'w') as file:
                json.dump(cases, file, indent=4)

    logging('Time taken: ' + str(total_time))

    event('Close tool', True, cases[-1]['case'])


main()
