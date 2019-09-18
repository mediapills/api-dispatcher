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
import boto3
import mock
import os
import subprocess
import unittest

from api_dispatcher.deployer import DeployerCreator, InvalidParameterError
from tests.unit.utils import PATH_TO_TEST_FILES, PATH_TO_CONFIGS, \
    mock_subproc_command, MockBoto3
from zappa.cli import ZappaCLI, ClickException


class DeployerTestCase(unittest.TestCase):

    cloud_type = None

    @mock.patch.object(ZappaCLI, 'deploy', return_value=True)
    @mock.patch.object(ZappaCLI, 'update', return_value=True)
    @mock.patch.object(ZappaCLI, 'undeploy', return_value=True)
    @mock.patch.object(
        subprocess, 'check_output', side_effect=mock_subproc_command
    )
    def _deploy_app_custom_settings(self, *args, **kwargs):
        app_deleted = True
        deployer = DeployerCreator.create_deployer(self.cloud_type)
        no_delete = kwargs.pop('no_delete', False)
        app_deployed = deployer.deploy_flask(**kwargs)
        if not no_delete:
            app_deleted = deployer.undeploy_flask()
        return app_deployed and app_deleted


class AWSDeployerFlaskTestCase(DeployerTestCase):

    cloud_type = 'aws'

    def test_deploy_app_aws_custom_params(self):
        test_params = {'script_loc': 'test_deployer.app', 'stage': 'dev'}
        self.assertTrue(self._deploy_app_custom_settings(**test_params))

    @mock.patch.object(boto3, 'client', return_value=MockBoto3())
    @mock.patch.object(boto3, 'resource', return_value=MockBoto3())
    @mock.patch.object(MockBoto3, 'Bucket')
    def test_deploy_app_aws_good_settings_file(self, *args):
        settings = os.path.join(PATH_TO_CONFIGS, 'aws', 'zappa_settings.json')
        test_params = {'deploy_settings': settings}
        self.assertTrue(self._deploy_app_custom_settings(**test_params))

    @mock.patch.object(ZappaCLI, 'deploy', side_effect=ClickException('test'))
    @mock.patch.object(ZappaCLI, 'undeploy', side_effect=ClickException('test'))
    def test_deploy_app_deployment_error(self, *args):
        settings = os.path.join(PATH_TO_CONFIGS, 'aws', 'zappa_settings.json')
        test_params = {'deploy_settings': settings}
        deployer = DeployerCreator.create_deployer(self.cloud_type)
        app_deployed = deployer.deploy_flask(**test_params)
        app_deleted = deployer.undeploy_flask()
        self.assertTrue(app_deployed is False and app_deleted is False)

    def test_update_app_after_deploy(self):
        test_params = {
            'script_loc': 'test_deployer.app',
            'stage': 'dev',
            'no_delete': True
        }
        self._deploy_app_custom_settings(**test_params)
        # Update previous deployment
        self.assertTrue(self._deploy_app_custom_settings(**test_params))

    def test_deploy_app_aws_no_settings(self):
        test_params = {'stage': 'dev'}
        with self.assertRaises(InvalidParameterError):
            self._deploy_app_custom_settings(**test_params)

    def test_deploy_app_aws_bad_settings_file_mult_stages(self):
        settings = os.path.join(
            PATH_TO_CONFIGS,
            'aws',
            'zappa_settings_multiple_stages.json'
        )
        test_params = {'deploy_settings': settings}
        with self.assertRaises(InvalidParameterError):
            self._deploy_app_custom_settings(**test_params)


class AWSDeployerSwaggerTestCase(DeployerTestCase):

    @mock.patch.object(boto3, 'client', return_value=MockBoto3())
    @mock.patch.object(boto3, 'resource', return_value=MockBoto3())
    def _deploy_swaggers(self, deploys, *args):
        deployer = DeployerCreator.create_deployer('aws')
        correct_deploys = []
        for dep_file in deploys:
            correct_deploys.append(deployer.deploy_swagger(dep_file))

        return deployer.undeploy_swagger() and all(correct_deploys)

    def test_deploy_api_gateway_with_openapi_spec(self):
        deploys = [
            os.path.join(PATH_TO_TEST_FILES, 'v3.0', 'petstore.yaml')
        ]
        self.assertFalse(self._deploy_swaggers(deploys))

    def test_deploy_api_gateway_multiple_openapi_spec(self):
        deploys = [
            os.path.join(PATH_TO_TEST_FILES, 'v3.0', 'petstore.yaml'),
            os.path.join(PATH_TO_TEST_FILES, 'v3.0', 'uspto.yaml')
        ]
        self.assertFalse(self._deploy_swaggers(deploys))


class GCPDeployerTestCase(DeployerTestCase):

    cloud_type = 'gcp'

    def test_deploy_app_gcp_no_settings_file(self):
        settings = {'script_loc': 'test_deployer.app'}
        self.assertTrue(self._deploy_app_custom_settings(**settings))

    def test_deploy_app_gcp_correct_settings_file(self):
        settings = {
            'deploy_settings': os.path.join(PATH_TO_CONFIGS, 'gcp', 'app.yaml')
        }
        self.assertTrue(self._deploy_app_custom_settings(**settings))


class AzureDeployerTestCase(DeployerTestCase):

    cloud_type = 'azure'

    @mock.patch.object(
        subprocess, 'check_output', side_effect=mock_subproc_command
    )
    def _deploy_app_custom_settings(self, *args, **kwargs):
        app_deleted = True
        deployer = DeployerCreator.create_deployer(self.cloud_type)
        no_delete = kwargs.pop('no_delete', False)
        app_deployed = deployer.deploy_flask(**kwargs)
        if not no_delete:
            app_deleted = deployer.undeploy_flask(kwargs.get('deploy_settings'))
        return app_deployed and app_deleted

    def test_deploy_app_azure_no_settings_file(self):
        settings = {'name': 'my-flask-app'}
        self.assertTrue(self._deploy_app_custom_settings(**settings))

    def test_deploy_app_azure_correct_settings_file(self):
        deploy_settings = os.path.join(
            PATH_TO_CONFIGS,
            'azure',
            'azure_settings.json'
        )
        settings = {'name': 'my-flask-app', 'deploy_settings': deploy_settings}
        self.assertTrue(self._deploy_app_custom_settings(**settings))

    def test_undeploy_invalid(self):
        deployer = DeployerCreator.create_deployer(self.cloud_type)
        with self.assertRaises(InvalidParameterError):
            deployer.undeploy_flask()
