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

with open('requirements.txt') as f:
    required = f.read().splitlines()

packages = find_packages() + ['data']


setup(
    name='api-dispatcher',
    version='0.0.1',
    author='Apache Software Foundation',
    author_email='dev@dlab.apache.org',
    url='http://dlab.apache.org/',
    description='This a swagger provider.',
    packages=packages,
    data_files=[
        ('', ['requirements.txt', 'Makefile'])
    ],
    include_package_data=True,
    install_requires=required
)
