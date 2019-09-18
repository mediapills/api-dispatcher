# *****************************************************************************
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# ******************************************************************************
import os
import unittest


def get_test_files(dir_name, include=None, exclude=None):
    """Gets all files recursively from given directory

    :type dir_name: str
    :param dir_name: directory name to search files in
    :type include: tuple
    :param include: file names to include
    :type exclude: tuple
    :param exclude: file names to exclude

    :rtype: list
    :return: list of files found recursively in given directory
    """
    all_files = []
    for entry in os.listdir(dir_name):
        full_path = os.path.join(dir_name, entry)
        if not exclude or (exclude and entry not in exclude):
            if os.path.isdir(full_path):
                _include = None if include and entry in include else include
                all_files = all_files + get_test_files(
                    full_path,
                    include=_include,
                    exclude=exclude
                )
            elif not include or (include and entry in include):
                all_files.append(full_path)

    return all_files


def create_tc(tests_data):
    """Creates a unittest TestCase with given generated tests

    :type tests_data: dict
    :param tests_data: dictionary with test names pattern as a key and list of
test methods as a value

    :rtype: unittest.TestCase()
    :return: test case with generated tests
    """
    test_case = unittest.TestCase

    def set_tests(test_name_pattern, tests_methods):
        for num_of_test, test in enumerate(tests_methods):
            test_name = 'test_' + test_name_pattern + '_{}'.format(num_of_test)
            setattr(test_case, test_name, test)

    for test_name, tests in tests_data.items():
        set_tests(test_name, tests)

    return test_case


def mock_subproc_command(command, *args, **kwargs):
    return_values = {
        'az webapp up -n test --dryrun': (
            '{"resourcegroup": "1"}'.encode('utf8')
        ),
        'az webapp up': (
            '{"app_url": "your-address"}'.encode('utf8')
        ),
        'az account': (
            '[{"isDefault": true, "name": "Test"}]'.encode('utf8')
        ),
        'gcloud app versions': (
            '[{"id": "1"}, {"id": "2"}]'.encode('utf8')
        ),
        'gcloud app deploy': '{"versions": [{"id": "1"}]}'.encode('utf8')
    }
    for ex_command, output in return_values.items():
        if command.startswith(ex_command):
            return output

    return ''.encode('utf8')


class MockBoto3(object):

    class MockExceptions(object):
        class BadRequestException(Exception):
            pass

    exceptions = MockExceptions()

    class Bucket(object):
        pass

    def __init__(self, *args):
        pass

    def delete_rest_api(self, **kwargs):
        pass

    def import_rest_api(self, **kwargs):
        return {'ResponseMetadata': {'HTTPStatusCode': 200}, 'id': 1}

    def create_deployment(self, **kwargs):
        raise self.exceptions.BadRequestException('bad request')

    def list_buckets(self, **kwargs):
        return {'Buckets': [{'Name': 'app-yi5aqnt2i'}]}


PATH_TO_TEST_FILES = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    '..',
    '..',
    'data',
    'examples'
)
PATH_TO_CONFIGS = os.path.join(
    PATH_TO_TEST_FILES,
    '..',
    'deploy_configs'
)
valid_test_data = get_test_files(
    PATH_TO_TEST_FILES,
    exclude=('petstore-separate', 'invalid')
)
invalid_test_data = get_test_files(
    PATH_TO_TEST_FILES,
    include=('invalid',),
    exclude=('petstore-without-required-spec-version.yaml',)
)
invalid_spec_version = get_test_files(
    PATH_TO_TEST_FILES,
    include=('petstore-without-required-spec-version.yaml',)
)
