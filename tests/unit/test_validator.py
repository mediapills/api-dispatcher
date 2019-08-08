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
import pytest
from api_dispatcher.validator import get_spec_validator


def get_test_files(dir_name, include=None, exclude=None):
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


PATH_TO_TEST_FILES = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..",
    "..",
    "data",
    "examples"
)
valid_test_data = get_test_files(
    PATH_TO_TEST_FILES,
    exclude=("petstore-separate", "invalid")
)
invalid_test_data = get_test_files(
    PATH_TO_TEST_FILES,
    include=("invalid",),
    exclude=("petstore-without-required-spec-version.yaml",)
)
spec_without_version = get_test_files(
    PATH_TO_TEST_FILES,
    include=("petstore-without-required-spec-version.yaml",)
)


@pytest.mark.parametrize("file", valid_test_data)
def test_validator_valid_specs(file):
    validator = get_spec_validator(file)
    assert validator.validate()


@pytest.mark.parametrize("file", invalid_test_data)
def test_validator_invalid_specs(file):
    validator = get_spec_validator(file)
    assert not validator.validate()


@pytest.mark.parametrize("file", spec_without_version)
def test_validator_invalid_spec_without_version(file):
    assert not get_spec_validator(file)
