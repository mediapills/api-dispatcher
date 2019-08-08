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
import yaml
from jsonschema.validators import validator_for

SCHEMAS_FOLDER = (os.path.dirname(__file__), "..", "data", "schemas")


class Validator:
    def __init__(self, spec_file):
        self._spec = Validator.load_file(spec_file)
        self.schema_path = None

    def validate(self, file=None):
        """Validates given Swagger/OpenAPI specification file """
        if not self.load_file_and_schema(file):
            return False

        valid_refs = self.validate_refs()
        valid_spec = self.validate_spec()
        return False if not valid_spec or not valid_refs else True

    def load_file_and_schema(self, file):
        """Loads specification and sets schema for validated file """
        if not self.schema_path or file:
            self._spec = Validator.load_file(file) if file else self._spec
            validator = get_spec_validator(self._spec)
            if validator.__class__ == Validator:
                return False

            self.schema_path = validator.schema_path

        return True

    def validate_spec(self):
        """Validates specification against corresponding schema"""
        schema = json.load(open(os.path.join(*self.schema_path)))
        validator = validator_for(schema)
        errors = validator(schema).iter_errors(self._spec)
        return False if len(list(errors)) > 0 else True

    def get_all_refs(self, spec, _refs_list=None):
        """Gets all references from given Swagger/OpenAPI specification file """
        if isinstance(spec, dict):
            for k, v in spec.items():
                if k == "$ref":
                    _refs_list.append(v)
                else:
                    self.get_all_refs(v, _refs_list)

        elif isinstance(spec, list):
            for item in spec:
                self.get_all_refs(item, _refs_list)

        return _refs_list

    def validate_refs(self):
        """Validates all references in specification file """
        refs_list = self.get_all_refs(spec=self._spec, _refs_list=[])
        for ref in refs_list:
            if not self.check_ref(self._spec, ref):
                return False

        return True

    @staticmethod
    def check_ref(spec, ref):
        """Validates given reference """
        path_to_obj = ref.split("/")[1:]
        item = spec
        for path in path_to_obj:
            item = item.get(path)
            if not item:
                return False

        return True

    @staticmethod
    def load_file(file):
        """Returns loaded specification file """
        if file:
            if isinstance(file, dict):
                return file
            if os.path.splitext(file)[1] == '.json':
                return json.load(open(file))
            elif os.path.splitext(file)[1] in ('.yml', '.yaml'):
                return yaml.safe_load(open(file))


class Swagger1Validator(Validator):

    def __init__(self, spec_file):
        super(Swagger1Validator, self).__init__(spec_file)
        self.schema_path = SCHEMAS_FOLDER + ("v1.2", "apiDeclaration.json")


class Swagger2Validator(Validator):

    def __init__(self, spec_file):
        super(Swagger2Validator, self).__init__(spec_file)
        self.schema_path = SCHEMAS_FOLDER + ("v2.0", "schema.json")


class OpenAPIValidator(Validator):

    def __init__(self, spec_file):
        super(OpenAPIValidator, self).__init__(spec_file)
        self.schema_path = SCHEMAS_FOLDER + ("v3.0", "schema.json")


def get_spec_validator(file):
    """Returns validator object for given specification file """
    spec = file if isinstance(file, dict) else Validator.load_file(file)
    for version_def in VALIDATORS_MAP:
        if spec.get(version_def):
            return VALIDATORS_MAP[version_def](spec)

    return Validator(spec)


VALIDATORS_MAP = {
    "openapi": OpenAPIValidator,
    "swagger": Swagger2Validator,
    "swaggerVersion": Swagger1Validator
}
