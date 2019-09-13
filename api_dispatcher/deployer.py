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
import json
import os
import random
import sys
import string
import subprocess
import time
import yaml
import zappa.cli
from abc import abstractmethod
from api_dispatcher.utils import load_file, LOG


class DeploymentError(Exception):
    pass


class InvalidParameterError(DeploymentError):
    pass


class APIImportError(DeploymentError):
    pass


class DeployerCreator(object):

    @staticmethod
    def create_deployer(cloud_type):
        """Given the cloud type, returns deployer object for AWS or GCP

        :type cloud_type: str
        :param cloud_type: Type of cloud to deploy

        :rtype: AWSDeployer / GCPDeployer
        :return: deployer object for AWS or GCP
        """
        cloud_dispatchers_map = {
            'aws': AWSDeployer,
            'gcp': GCPDeployer,
            'azure': AzureDeployer
        }
        return cloud_dispatchers_map[cloud_type.lower()]()


class BaseDeployer(object):

    @abstractmethod
    def deploy_flask(self, *args, **kwargs):
        pass

    @abstractmethod
    def undeploy_flask(self, *args, **kwargs):
        pass


class AWSDeployer(BaseDeployer):

    def __init__(self):
        """Initializes AWS clients"""
        self._zappa_cli = zappa.cli.ZappaCLI()
        self._deploy_config = None
        self._stage = None
        self._deployed_apigwids = []

    def create_config(self, stage, script_loc, project_name):
        """Creates a deployment config for AWS

        :type stage: str
        :param stage: stage from deploy settings file to publish
        :type script_loc: str
        :param script_loc: Flask app location in `filename.variable_name`
        :type project_name: str
        :param project_name: project name for deployment

        :rtype: dict
        :return: deployment configuration for publishing Flask app to App Engine
        """
        bucket_name = 'app-{}'.format(''.join(
            random.choice(string.ascii_lowercase + string.digits)
            for _ in range(9)
        ))
        session = boto3.session.Session()
        region = session.region_name
        profile_name = session.profile_name or 'default'
        config = {
            stage: {
                'app_function': script_loc,
                'aws_region': region,
                'profile_name': profile_name,
                'project_name': project_name or 'DeployedFlaskApp',
                'runtime': 'python{}'.format(
                    '2.7' if sys.version_info[0] < 3 else '3.7'
                ),
                's3_bucket': bucket_name,
                'delete_local_zip': True
            }
        }
        return config

    def load_deploy_config(self, deploy_settings, stage):
        """Loads deployment config from file

        :type deploy_settings: str
        :param deploy_settings: JSON-file with deployment settings
        :type stage: str
        :param stage: stage from deploy settings file to load

        :rtype: str
        :return: deploy settings file name
        """
        with open(deploy_settings) as fp:
            self._deploy_config = json.load(fp)
        if not stage:
            if len(self._deploy_config) > 1:
                # No stage defined to deploy
                raise InvalidParameterError(
                    'Stage should be defined if settings file '
                    'contains more than one config'
                )

            stage = next(iter(self._deploy_config))

        self._stage = stage
        return deploy_settings

    def set_deploy_config(self, script_loc, stage, project_name):
        """Writes deployment config to file

        :type script_loc: str
        :param script_loc: Flask app location in `filename.variable_name`
        :type stage: str
        :param stage: stage from deploy settings file to publish
        :type project_name: str
        :param project_name: project name for deployment

        :rtype: str
        :return: deploy settings file name
        """
        if not (script_loc and stage):
            raise InvalidParameterError(
                'Stage and script location should be defined if settings file '
                'is not provided'
            )

        deploy_settings = 'zappa_settings.json'
        self._deploy_config = self.create_config(
            stage, script_loc, project_name
        )
        self._stage = stage
        with open(deploy_settings, 'w') as settings_file:
            stringified_json = json.dumps(
                self._deploy_config, sort_keys=True, indent=4
            )
            settings_file.write(stringified_json)

        return deploy_settings

    def deploy_app(self, deploy_settings):
        """Deploys Flask-application from current folder to AWS

        :type deploy_settings: str
        :param deploy_settings: JSON-file with deployment settings

        :rtype: bool
        :return: True if app is deployed, else False
        """
        self._zappa_cli.api_stage = self._stage
        self._zappa_cli.load_settings(deploy_settings)

        versions = self._zappa_cli.zappa.get_lambda_function_versions(
            self._zappa_cli.lambda_name
        )
        try:
            if (
                    (versions and self._zappa_cli.update()) or
                    self._zappa_cli.deploy()
            ):
                return True

        except zappa.cli.ClickException as e:
            LOG.error(e)
            return False

    def deploy_flask(self, deploy_settings=None, script_loc=None, stage=None,
                     project_name=None):
        """Loads deployment settings and deploys Flask-application
from current folder to AWS

        :type deploy_settings: str
        :param deploy_settings: JSON-file with deployment settings
        :type script_loc: str
        :param script_loc: Flask app location in `filename.variable_name`
        :type stage: str
        :param stage: stage to deploy
        :type project_name: str
        :param project_name: project name for deployment

        :rtype: bool
        :return: True if app is deployed, else False
        """
        settings = (
            self.set_deploy_config(script_loc, stage, project_name)
            if not deploy_settings
            else self.load_deploy_config(deploy_settings, stage)
        )

        return self.deploy_app(settings)

    def delete_bucket(self):
        """Deletes bucket for deployed application """
        bucket_client = boto3.resource('s3')
        created_bucket = self._deploy_config[self._stage]['s3_bucket']
        buckets = [
            bucket['Name']
            for bucket in boto3.client('s3').list_buckets()['Buckets']
        ]
        if created_bucket in buckets:
            bucket = bucket_client.Bucket(created_bucket)
            bucket.objects.all().delete()
            bucket.delete()

    def undeploy_flask(self, remove_logs=False):
        """Removes deployed API and Flask app from AWS

        :type remove_logs: bool
        :param remove_logs: Whether to remove logs for AWS Lambda
        """
        success = True
        settings_file = 'tmp_settings.json'
        if self._deploy_config:
            with open(settings_file, 'w') as fp:
                json.dump(self._deploy_config, fp, sort_keys=True, indent=4)

        self._zappa_cli.api_stage = self._stage
        self._zappa_cli.load_settings(settings_file)
        try:
            self._zappa_cli.undeploy(no_confirm=True, remove_logs=remove_logs)
        except zappa.cli.ClickException as e:
            LOG.error(e)
            success = False
        finally:
            if self._deploy_config and self._stage:
                self.delete_bucket()
            os.remove(settings_file)

        return success

    def deploy_swagger(self, openapi_file, stage='dev'):
        """Deploys API Gateway from OpenAPI specification file

        :type openapi_file: str/dict
        :param openapi_file: OpenAPI spec to deploy
        :type stage: str
        :param stage: stage from deploy settings file to deploy

        :rtype: bool
        :return: True if API Gateway is deployed, else False
        """
        apigateway_client = boto3.client('apigateway')
        openapi_spec = load_file(openapi_file)
        byteslike_spec = json.dumps(openapi_spec).encode('utf8')
        result = apigateway_client.import_rest_api(body=byteslike_spec)
        success = int(result['ResponseMetadata']['HTTPStatusCode']) < 300
        if success:
            try:
                apigateway_client.create_deployment(
                    restApiId=result['id'],
                    stageName=stage
                )
            except apigateway_client.exceptions.BadRequestException:
                success = False

            self._deployed_apigwids.append(result['id'])

        return success

    def undeploy_swagger(self, api_ids=None):
        """Deletes API Gateway by API Gateway ids

        :type api_ids: list
        :param api_ids: API Gateway ids to delete

        :rtype: bool
        :return: True if at least one API Gateway is deleted, else False
        """
        apigateway_client = boto3.client('apigateway')
        api_gw_ids = api_ids or self._deployed_apigwids
        for restApiId in api_gw_ids:
            apigateway_client.delete_rest_api(restApiId=restApiId)
            # Cooldown time between API Gateways deletion
            if len(api_gw_ids) > 1:
                time.sleep(60)

        return len(api_gw_ids) > 0


class GCPDeployer(BaseDeployer):

    def create_config_file(self, script_loc, service):
        """Creates a deployment config for GCP

        :type script_loc: str
        :param script_loc: Flask app location in `filename.variable_name`
        :type service: str
        :param service: service name to deploy

        :rtype: dict
        :return: deployment configuration for publishing Flask app to App Engine
        """
        config = {}
        if sys.version_info[0] < 3:
            runtime = 'python27'
            handlers = script_loc
            config.update({
                'threadsafe': True
            })
        else:
            runtime = 'python37'
            handlers = 'auto'

        config.update({
            'runtime': runtime,
            'service': service,
            'handlers': [{'url': '/.*', 'script': handlers}],
            'env': 'standard'
        })
        return config

    def deploy_flask(self, deploy_settings=None, script_loc=None,
                     service='default'):
        """Deploys Flask-application from current folder to GCP

        :type deploy_settings: str
        :param deploy_settings: YAML-file with deployment settings
        :type script_loc: str
        :param script_loc: Flask app location in `filename.variable_name`
        :type service: str
        :param service: service name to deploy

        :rtype: bool
        :return: True if app is deployed, else False
        """
        if not deploy_settings:
            config = self.create_config_file(script_loc, service)
            with open('app.yaml', 'w+') as fp:
                yaml.dump(config, fp, default_flow_style=False)

        deploy_cmd = 'gcloud app deploy --quiet {}'.format(
            deploy_settings if deploy_settings else ''
        )
        out = subprocess.check_output(deploy_cmd)
        return 'Deployed service' in out.decode('utf8')

    def undeploy_flask(self, service_name='default'):
        """Deletes deployed versions for specified API Engine service

        :type service_name: str
        :param service_name: service name to delete API Engine version for

        :rtype: bool
        :return: True if all versions were deleted
        """
        versions_cmd = 'gcloud app versions list --service {} ' \
                       '--format json'.format(service_name)
        versions_json_list = subprocess.check_output(versions_cmd)
        versions_to_delete = []
        for version in json.loads(versions_json_list.decode('utf8')):
            if int(version['traffic_split']) == 0:
                versions_to_delete.append(version['id'])

        versions_delete_cmd = 'gcloud app versions delete --service {} ' \
                              '--quiet '.format(service_name)
        versions_delete_cmd += ' '.join(versions_to_delete)
        subprocess.check_output(versions_delete_cmd)
        return True


class AzureDeployer(BaseDeployer):

    def __init__(self):
        self._resource_group = None
        self._subscription = None

    def define_parameters(self, deploy_settings):
        """Loads deployment parameters either from given JSON-file or
from local Azure config

        :type deploy_settings: str
        :param deploy_settings: JSON-file name with deployment parameters

        :rtype: str
        :return: CLI deployment parameters in '--<param> <value>' format
        """
        params = ''
        if deploy_settings:
            with open(deploy_settings) as fp:
                settings_json = json.load(fp)

            params += '--logs --verbose --output json '
            arguments = [
                'location', 'plan', 'sku', 'resource-group', 'subscription'
            ]
            self._resource_group = settings_json.get('resource-group')
            self._subscription = settings_json.get('subscription')
            for arg in arguments:
                arg_value = settings_json.get(arg)
                if arg_value:
                    params += '--{} {} '.format(arg, arg_value)

        else:
            subs_json_list = subprocess.check_output('az account list')
            for sub_info in json.loads(subs_json_list.decode('utf8')):
                if int(sub_info['isDefault']):
                    self._subscription = sub_info['name']
            result = subprocess.check_output('az webapp up -n test --dryrun')
            self._resource_group = result['resourcegroup']

        return params

    def deploy_flask(self, name, deploy_settings=None):
        """Deploys Flask-application from current folder to Azure

        :type name: str
        :param name: name of the deployed application
        :type deploy_settings: str
        :param deploy_settings: JSON-file name with deployment parameters

        :rtype: bool
        :return: True if app is deployed, else False
        """
        params = self.define_parameters(deploy_settings)
        result = subprocess.check_output(
            'az webapp up -n {} {}'.format(name, params)
        )
        LOG.info(result.decode('utf8'))
        return True

    def undeploy_flask(self, deploy_settings=None):
        """Deletes resource group with deployed application

        :type deploy_settings: str
        :param deploy_settings: JSON-file name with deployment parameters

        :rtype: bool
        :return: True if resource group is deleted
        """
        if deploy_settings:
            with open(deploy_settings) as fp:
                settings_json = json.load(fp)
            self._resource_group = settings_json.get('resource-group')
            self._subscription = settings_json.get('subscription')
        if not self._resource_group or not self._subscription:
            raise InvalidParameterError(
                'You should specify resource group and subscription '
                'in your settings file in order to remove you application stack'
            )

        result = subprocess.check_output(
            'az group delete -n {} --yes --subscription {}'.format(
                self._resource_group, self._subscription)
        )
        LOG.info(result.decode('utf8'))
        return True
