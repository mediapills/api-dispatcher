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


class Validator:

    def __init__(self, spec_file=None):
        if spec_file:
            self._spec = yaml.safe_load(open(spec_file))

        self.valid_refs = True
        self.valid_schema = True

    def validate_spec(self, file=None):
        """Validates given Swagger/OpenAPI specification file against corresponding schema """

        if file:
            self._spec = yaml.safe_load(open(file))

        schema_path = self._get_spec_schema_file()
        if not schema_path:
            print("Unknown Swagger/OpenAPI specification version. Available schemas: 1.2, 2.0, 3.0.x")
            return -1

        schema = json.load(open(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "..", "openapi_specs", schema_path[0], schema_path[1]
        )))

        self.validate_refs(self._spec)

        validator = validator_for(schema)(schema)
        for error in validator.iter_errors(self._spec):
            print(error)
            self.valid_schema = False

        if not self.valid_schema or not self.valid_refs:
            return -1

        return 1

    def validate_refs(self, spec, path_to_ref="schema"):
        """Validates references in given Swagger/OpenAPI specification file

        :param spec: OpenAPI/Swagger specification object or its part
        :type spec: dict
        :param path_to_ref: Path to found reference
        :type path_to_ref: str

        """
        if isinstance(spec, dict):
            for k, v in spec.items():
                if k == "$ref":
                    self._check_ref(v, path_to_ref)
                self.validate_refs(v, path_to_ref + "['" + k + "']")

        elif isinstance(spec, list):
            for index, item in enumerate(spec):
                self.validate_refs(item, path_to_ref + "['" + str(index) + "']")

    def _check_ref(self, ref, path_to_ref):
        ref = ref.lstrip("#")
        path_to_obj = ref.split("/")[1:]
        item = self._spec
        for path in path_to_obj:
            item = item.get(path)
            if not item:
                print("Invalid reference '{0}' in path: {1}".format(ref, path_to_ref))
                self.valid_refs = False
                return

    def _get_spec_schema_file(self):
        spec_versions_map = {
            "openapi": ("v3.0", "schema.json"),
            "swagger": ("v2.0", "schema.json"),
            "swaggerVersion": ("v1.2", "apiDeclaration.json")
        }
        for version_def in spec_versions_map:
            if self._spec.get(version_def):
                return spec_versions_map[version_def]
