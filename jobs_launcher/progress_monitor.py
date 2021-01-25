import os
import json
import time
import argparse
import hashlib

from image_service_client import ISClient
from ums_client import create_ums_client
from minio_client import create_mc_client
from core.config import *
import traceback

res = []
transferred_test_cases = []

is_client = None
ums_client_prod = create_ums_client("PROD")
ums_client_dev = create_ums_client("DEV")
minio_client_prod = None
minio_client_dev = None
if ums_client_prod:
    minio_client_prod = create_mc_client(ums_client_prod.job_id)
if ums_client_dev:
    minio_client_dev = create_mc_client(ums_client_dev.job_id)
try:
    is_client = ISClient(
        url=os.getenv("IS_URL"),
        login=os.getenv("IS_LOGIN"),
        password=os.getenv("IS_PASSWORD")
    )
    main_logger.info("Image Service client created for url: {}".format(is_client.url))
except Exception as e:
    main_logger.error("Can't create Image Service client for url: {}. Error: {}".format(is_client.url, str(e)))


def render_color_full_path(session_dir, suite_name, render_color_path):
    return os.path.realpath(os.path.join(session_dir, suite_name, render_color_path))


def get_cases_existence_info_by_hashes(session_dir, suite_name, test_cases):
    cases_hashes_info = {}
    cases_hashes = {}
    for case in test_cases:
        with open(os.path.join(session_dir, suite_name, case + '_RPR.json')) as case_file:
            case_file_data = json.load(case_file)[0]
            with open(render_color_full_path(session_dir, suite_name, case_file_data['render_color_path']), 'rb') as img:
                bytes_data = img.read()
                cases_hashes[case] = hashlib.md5(bytes_data).hexdigest()

    hash_info_from_is = is_client.get_existence_info_by_hash(
        [case_hash for case, case_hash in cases_hashes.items() if case_hash]
    )
    if hash_info_from_is:
        cases_hashes_info = {
            case: hash_info_from_is[case_hash]
            for case, case_hash in cases_hashes.items() if case_hash in hash_info_from_is
        }
    return cases_hashes_info


def send_finished_cases(session_dir, suite_name):


    if os.path.exists(os.path.join(session_dir, suite_name, 'test_cases.json')):
        test_cases_path = os.path.join(session_dir, suite_name, 'test_cases.json')
        with open(test_cases_path) as test_cases_file:
            global transferred_test_cases
            test_cases = json.load(test_cases_file)
        # Blender, Maya, Core and Viewer has different case name
        if 'case' in test_cases[0]:
            name_key = 'case'
        elif 'name' in test_cases[0]:
            name_key = 'name'
        else:
            name_key = 'scene'
    else:
        # case of Max
        test_cases_path = os.path.join(session_dir, suite_name, 'case_list.json')
        with open(test_cases_path) as test_cases_file:
            global transferred_test_cases
            test_cases = json.load(test_cases_file)['cases']
        name_key = 'name'
    new_test_cases = {}
    for test_case in test_cases:
        if test_case['status'] in ('skipped', 'error', 'done', 'passed') and not test_case[name_key] in transferred_test_cases:
            new_test_cases[test_case[name_key]] = test_case['status']
            if 'aovs' in test_case:
                for aov in test_case['aovs']:
                    new_test_cases[test_case[name_key] + aov['aov']] = aov['status']

    new_cases_existence_hashes_info = get_cases_existence_info_by_hashes(session_dir, suite_name, new_test_cases) if is_client else {}
    print('Got hashes info from image service:\n{}'.format(json.dumps(new_cases_existence_hashes_info, indent=2)))

    if ums_client_prod:
        ums_client_prod.get_suite_id_by_name(suite_name)
        minio_client_prod.upload_file(test_cases_path, ums_client_prod.build_id, ums_client_prod.suite_id)
    if ums_client_dev:
        ums_client_dev.get_suite_id_by_name(suite_name)
        minio_client_dev.upload_file(test_cases_path, ums_client_dev.build_id, ums_client_dev.suite_id)
    for test_case in new_test_cases:
        print('Sending artefacts & images for: {}'.format(test_case))
        with open(os.path.join(session_dir, suite_name, test_case + '_RPR.json')) as case_file:
            case_file_data = json.load(case_file)[0]

            if test_case in new_cases_existence_hashes_info and \
                    new_cases_existence_hashes_info[test_case] and \
                    'id' in new_cases_existence_hashes_info[test_case]:
                image_id = new_cases_existence_hashes_info[test_case]['id']
                print("Use id found by hash for case: {} id: {}".format(test_case, image_id))
            else:
                image_id = is_client.send_image(render_color_full_path(session_dir, suite_name, case_file_data[
                    'render_color_path'])) if is_client else -1
                print("Upload new image for case: {} and get image id: {}".format(test_case, image_id))
            case_file_data['image_service_id'] = image_id

        with open(os.path.join(session_dir, suite_name, test_case + '_RPR.json'), 'w') as case_file:
            json.dump([case_file_data], case_file, indent=4, sort_keys=True)

    transferred_test_cases += list(new_test_cases.keys())
    diff = len(test_cases) - len(transferred_test_cases)
    print('Monitor is waiting {} cases'.format(diff))
    if diff <= 0:
        return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', required=False, default=5, type=int, help="time interval")
    parser.add_argument('--session_dir', required=True, type=str, help='session dir')
    parser.add_argument('--suite_name', required=True, type=str, help='suite name')

    args = parser.parse_args()

    check = 1
    fails_in_succession = 0
    while True:
        try:
            time.sleep(args.interval)
            print('Check number {}'.format(check))
            check += 1
            result = send_finished_cases(args.session_dir, args.suite_name)
            fails_in_succession = 0
            if result:
                break
        except Exception as e:
            fails_in_succession += 1
            main_logger.error("Failed iteration of progress monitor: {}".format(e))
            main_logger.error("Traceback: {}".format(traceback.format_exc()))
        if MAX_UMS_SEND_RETRIES == fails_in_succession:
            break
