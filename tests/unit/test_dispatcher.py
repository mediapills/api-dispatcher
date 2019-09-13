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

from api_dispatcher.dispatcher import FlaskDispatcher
from tests.unit.utils import create_tc, valid_test_data, invalid_test_data, \
    invalid_spec_version, PATH_TO_TEST_FILES


valid_test_data = list(map(lambda x: [x, True], valid_test_data))
invalid_test_data = list(map(lambda x: [x, False], invalid_test_data))
invalid_spec_version = list(map(lambda x: [x, False], invalid_spec_version))


def generate_tests_valid():
    tests = []
    for data in valid_test_data:
        def test(self, data=data):
            app = FlaskDispatcher()
            self.assertEqual(app.add_api(data[0]), data[1])
        tests.append(test)

    return tests


def generate_tests_invalid():
    tests = []
    test_data = invalid_test_data + invalid_spec_version
    for data in test_data:
        def test(self, data=data):
            app = FlaskDispatcher()
            self.assertEqual(app.add_api(data[0]), data[1])
        tests.append(test)

    return tests


def listPets():
    pass


def showPetById():
    pass


class TestDispatcher(create_tc(
    {
        'valid_spec': generate_tests_valid(),
        'invalid_spec': generate_tests_invalid()
    }
)):

    def test_validator_valid_specs_existing_handlers(self):
        app = FlaskDispatcher()
        self.assertTrue(
            app.add_api(
                os.path.join(
                    PATH_TO_TEST_FILES, 'v2.0', 'json', 'petstore.json'
                ),
                methods_module=os.path.abspath(__file__)
            )
        )

    def test_validator_valid_specs_invalid_module(self):
        app = FlaskDispatcher()
        self.assertTrue(
            app.add_api(
                os.path.join(
                    PATH_TO_TEST_FILES, 'v2.0', 'json', 'petstore.json'
                ),
                methods_module='foo'
            )
        )
