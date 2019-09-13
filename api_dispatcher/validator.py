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
import os
from api_dispatcher.utils import LOG, load_file
from jsonschema.validators import validator_for

SCHEMAS_FOLDER = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'data', 'schemas'
)


class Validator(object):

    def __init__(self, spec_file):
        """Loads Swagger specification

        :type spec_file: Union[str, dict]
        :param spec_file: Swagger specification file
        """
        self._spec = load_file(spec_file)
        self.schema = None

    def validate(self, filename=None):
        """Validates given Swagger/OpenAPI specification file

        :type filename: str
        :param filename: file name of specification to validate

        :rtype: bool
        :return: whether specification and references are valid
        """
        if not self.load_file_and_schema(filename) or not self._spec:
            return False

        valid_refs = self.validate_refs()
        valid_spec = self.validate_spec()
        return valid_spec and valid_refs

    def load_file_and_schema(self, filename):
        """Loads specification and sets schema for validated file

        :type filename: str
        :param filename: file name to load

        :rtype: bool
        :return: whether specification is loaded
        """
        if isinstance(filename, str):
            validator = create_validator(filename)
            if not validator:
                return False

            self._spec = load_file(filename)
            self.schema = validator.schema
            return True

        if not filename:
            return True

        return False

    def validate_spec(self):
        """Validates specification against corresponding schema

        :rtype: bool
        :return: whether specification is valid against corresponding schema
        """
        validator = validator_for(self.schema)
        errors = validator(self.schema).iter_errors(self._spec)
        return not bool(list(errors))

    def get_all_refs(self, spec):
        """Gets all references from given Swagger/OpenAPI specification

        :type spec: Union[dict, list]
        :param spec: Swagger/OpenAPI specification

        :rtype: list
        :return: list of all references from specification
        """
        for k, v in (
            spec.items() if isinstance(spec, dict) else
            enumerate(spec) if isinstance(spec, list) else []
        ):
            if k == '$ref':
                LOG.info(v)
                yield v
            elif isinstance(v, (dict, list)):
                for result in self.get_all_refs(v):
                    yield result

    def validate_refs(self):
        """Validates all references in specification file

        :rtype: bool
        :return: True if all references are valid, else False
        """
        refs_list = self.get_all_refs(spec=self._spec)
        for ref in refs_list:
            if not self.check_ref(self._spec, ref):
                return False

        return True

    @staticmethod
    def check_ref(spec, ref):
        """Validates given reference

        :type spec: dict
        :param spec: specification object to check reference against
        :type ref: str
        :param ref: reference string

        :rtype: bool
        :return: True if reference is valid, else False
        """
        path_to_obj = ref.split('/')[1:]
        item = spec
        for path in path_to_obj:
            item = item.get(path)
            if not item:
                return False

        return True


def create_validator(spec):
    """Returns validator object for given specification file

    :type spec: Union[str, dict]
    :param spec: file name or Swagger specification to validate

    :raise InvalidSpecificationError: raised when given Swagger specification
does not contain Swagger version used to describe API

    :rtype: Validator
    :return: Validator object with validation schema path defined
    """
    if not isinstance(spec, dict):
        spec = load_file(spec)

    config_path = os.path.join(os.path.dirname(__file__), 'schemas_config.json')
    with open(config_path) as config:
        specs_info = json.load(config)

    for version_def in specs_info.values():
        if spec.get(version_def['schema_definition']):
            validator = Validator(spec)
            path = os.path.join(SCHEMAS_FOLDER, *version_def['schema_path'])
            with open(path) as schema:
                validator.schema = json.load(schema)
            return validator

    LOG.error('Could not get validator for the given file')
