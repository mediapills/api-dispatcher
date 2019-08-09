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

from setuptools import setup, find_packages
import os


def get_data_files(dir_name):
    all_files = []
    for entry in os.listdir(dir_name):
        full_path = os.path.join(dir_name, entry)
        if os.path.isdir(full_path):
            all_files = all_files + get_data_files(full_path)
        else:
            all_files.append(full_path)

    return all_files


examples = get_data_files(os.path.join('data', 'examples'))
schemas = get_data_files(os.path.join('data', 'schemas'))

setup(
    name='api-dispatcher',
    version='0.0.1',
    author='Apache Software Foundation',
    author_email='dev@dlab.apache.org',
    url='http://dlab.apache.org/',
    description='This a swagger provider.',
    packages=find_packages(),
    data_files=[('', examples + schemas)]
)
