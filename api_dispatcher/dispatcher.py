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
import inspect
import os
import re
import sys
from flask import Flask
from api_dispatcher.validator import create_validator
from api_dispatcher.utils import LOG, load_file

PARAM_TYPES_MAP = {'integer': 'int'}


class FlaskDispatcher(Flask):

    def __init__(self, import_name='', *args, **kwargs):
        """Initialize Flask

        :type import_name: str
        :param import_name: name of Flask application
        """
        super(FlaskDispatcher, self).__init__(import_name, *args, **kwargs)
        self._servers = []
        self._mapped_urls = []
        self._methods_module = None

    @staticmethod
    def _get_param_type(param_spec):
        """Finds parameter type in given specification

        :type param_spec: dict
        :param param_spec: parameter specification object

        :rtype: str
        :return: argument type
        """
        param_spec = param_spec.get('schema', param_spec)
        return PARAM_TYPES_MAP.get(
            param_spec.get('type'), param_spec.get('type')
        )

    @staticmethod
    def _build_typed_arg(arg, arg_type):
        """Builds typed argument

        :type arg: str
        :param arg: path argument name
        :type arg_type: str
        :param arg_type: path argument type

        :rtype: str
        :return: composed typed argument in `<type:name>` format
        """
        return (arg[0] + arg_type + ':' + arg[1:]) if arg else arg

    def _add_types_to_path(self, path, params):
        """Replaces arguments in path with typed arguments

        :type path: str
        :param path: base path
        :type params: dict
        :param params: path parameters specification

        :rtype: str
        :return: path with arguments with types
        """
        if params:
            converted_args = self._convert_arguments(path, params)
            for old_arg, new_arg in converted_args.items():
                path = path.replace(old_arg, new_arg)

        return path

    def _convert_arguments(self, path, params):
        """Assigns types to arguments from path: <id> -> <str:id>

        :type path: str
        :param path: base path
        :type params: dict
        :param params: path argument type

        :rtype: dict
        :return: `argument:typed_argument` format object
        """
        arg_type_field = 'paramType' if self._old_spec_version else 'in'
        args = {arg: arg for arg in re.findall(r'<\w+>', path)}
        for param in params:
            name = '<' + param['name'] + '>'
            if name in args and param[arg_type_field] == 'path':
                param_type = self._get_param_type(param)
                args[name] = self._build_typed_arg(args[name], param_type)

        return args

    def _find_caller(self):
        """Locates the caller module of dispatcher

        :rtype: str
        :return: path to script that invoked invoked dispatcher
        """
        stack_trace = inspect.stack()
        for frame in stack_trace:
            if frame[3] == '<module>':
                return frame[1]

    def _get_handler(self, path, method):
        """Finds endpoint handler method by path from specification file

        :type path: str
        :param path: path to file with handler method
        :type method: str
        :param method: handler function name

        :rtype: object
        :return: located handler function
        """
        if method:
            path = path.split('.') if path else []
            caller_module = self._methods_module or self._find_caller()
            package = (
                path[-1] if len(path) > 0 else
                os.path.splitext(os.path.basename(caller_module))[0]
            )
            sys.path.append(
                os.path.join(os.path.dirname(caller_module), *path[:-1])
            )
            try:
                module = __import__(package)
                return getattr(module, method)
            except ImportError:
                LOG.error('Module {} not found'.format(package))
            except AttributeError:
                LOG.error('Handler {} not found in {} module'.format(
                    method, package
                ))

    def _config_app(self):
        """Sets app name from specification """
        self.name = self.spec.get('info', {}).get('title', 'Unnamed')

    def _get_servers(self):
        """Finds servers URL from specification

        :rtype: list
        :return: list with server URLs found in specification
        """
        if self._old_spec_version:
            return [self.spec['basePath']]

        servers = self.spec.get('servers')
        if servers:
            return [server['url'] for server in servers]

        return [self.spec.get('host', '') + self.spec.get('basePath', '')]

    def _add_paths_to_app(self, paths):
        """Assign url rules to app

        :type paths: list
        :param paths: list of paths specification objects
        """
        for path in paths:
            if (path['rule'], path['methods']) not in self._mapped_urls:
                self.add_url_rule(**path)
                self._mapped_urls.append((path['rule'], path['methods']))

    def _create_rule(self, path, method, method_info):
        """Builds endpoint rule for Flask

        :type path: str
        :param path: path for URL rule mapping
        :type method:
        :param method: allowed HTTP-method
        :type method_info: dict
        :param method_info: endpoint specification with parameters,
script location etc.

        :rtype: list
        :return: URL-rule object wrapped to list
        """
        func = self._get_handler(
            method_info.get('x-swagger-router-controller', ''),
            method_info.get('operationId', '')
        )
        path = self._add_types_to_path(path, method_info.get('parameters'))
        return dict([
            ('rule', path),
            ('view_func', func) if func else ('endpoint', path),
            ('methods', [method.upper()])
        ])

    def _get_paths_swagger(self):
        """Returns paths information either from Swagger specification

        :rtype: list
        :return: list of URL-rules extracted from Swagger specification
        """
        paths = []
        for path_info in self.spec['apis']:
            path = path_info['path'].replace('{', '<').replace('}', '>')
            for method_info in path_info['operations']:
                paths.append(
                    self._create_rule(path, method_info['method'], method_info)
                )

        return paths

    def _get_paths_openapi(self):
        """Returns paths information either from OpenAPI specification

        :rtype: list
        :return: list of URL-rules extracted from OpenAPI specification
        """
        paths = []
        for path, path_info in self.spec['paths'].items():
            path = path.replace('{', '<').replace('}', '>')
            for method, method_info in path_info.items():
                paths.append(self._create_rule(path, method, method_info))

        return paths

    def _get_paths(self):
        """Returns paths information either from Swagger or OpenAPI spec

        :rtype: list
        :return: list of URL-rules extracted from specification
        """
        return self._get_paths_swagger() if self._old_spec_version else \
            self._get_paths_openapi()

    def _load_spec(self, spec):
        """Loads specification file

        :type spec: str
        :param spec: filename with Swagger/OpenAPI specification to load
        """
        self.spec = load_file(spec)
        self.validator = create_validator(spec)
        self._old_spec_version = self.spec.get('swaggerVersion') is not None

    def add_api(self, spec_file, overwrite_name=True, methods_module=None):
        """Adds API information and routing to app from specification file

        :type spec_file: str/dict
        :param spec_file: Swagger specification file
        :type overwrite_name: bool
        :param overwrite_name: whether to overwrite app name with new API title
        :type methods_module: str
        :param methods_module: optional path to module with handlers methods

        :rtype: bool
        :return: True if specification is valid and API is added to Flask app,
else False
        """
        self._load_spec(spec_file)
        self._methods_module = methods_module
        if self.validator and self.validator.validate():
            self._config_app() if overwrite_name else None
            self._add_paths_to_app(self._get_paths())
            self._servers.extend(self._get_servers())
            return True

        return False
