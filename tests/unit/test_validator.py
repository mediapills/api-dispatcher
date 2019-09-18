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
from api_dispatcher.validator import create_validator
from tests.unit.utils import create_tc, valid_test_data, invalid_test_data, \
    invalid_spec_version, PATH_TO_TEST_FILES


valid_test_data = list(map(lambda x: [x, True], valid_test_data))
invalid_test_data = list(map(lambda x: [x, False], invalid_test_data))
invalid_spec_version = list(map(lambda x: [x, None], invalid_spec_version))


def generate_tests_valid():
    tests = []
    for data in valid_test_data:
        def test(self, data=data):
            validator = create_validator(data[0])
            self.assertEqual(validator.validate(), data[1])
        tests.append(test)

    return tests


def generate_tests_invalid():
    tests = []
    for data in invalid_test_data:
        def test(self, data=data):
            validator = create_validator(data[0])
            self.assertEqual(validator.validate(data[0]), data[1])
        tests.append(test)

    return tests


def generate_tests_invalid_version():
    tests = []
    for data in invalid_spec_version:
        def test(self, data=data):
            self.assertEqual(create_validator(data[0]), data[1])
        tests.append(test)

    return tests


class ValidatorTestCase(create_tc(
    {
        'valid': generate_tests_valid(),
        'invalid': generate_tests_invalid(),
        'invalid_spec_version': generate_tests_invalid_version()
    }
)):

    def test_validator_invalid_loaded_spec_version(self):
        validator = create_validator(
            os.path.join(PATH_TO_TEST_FILES, 'v3.0', 'petstore.yaml')
        )
        self.assertFalse(
            validator.validate(
                os.path.join(
                    PATH_TO_TEST_FILES,
                    'invalid',
                    'v3.0',
                    'petstore-without-required-spec-version.yaml'
                )
            )
        )

    def test_validator_invalid_value_to_load(self):
        validator = create_validator(
            os.path.join(PATH_TO_TEST_FILES, 'v3.0', 'petstore.yaml')
        )
        self.assertFalse(validator.validate(True))
