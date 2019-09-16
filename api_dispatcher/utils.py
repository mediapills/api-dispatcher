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
import json
import logging
import os
import yaml


logging.basicConfig(
    format='[%(asctime)s] - %(levelname)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
LOG = logging.getLogger('api-dispatcher')


def load_file(filename):
    """Returns loaded specification file

    :type filename: Union[str, dict]
    :param filename: file name to load

    :rtype: dict
    :return: loaded Swagger specification object
    """
    if isinstance(filename, dict):
        return filename
    with open(filename) as fp:
        ext = os.path.splitext(filename)[1]
        if ext == '.json':
            return json.load(fp)
        if ext in ('.yml', '.yaml'):
            return yaml.safe_load(fp)
