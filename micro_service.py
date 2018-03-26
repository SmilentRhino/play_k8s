#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for alexrhino service
"""

import os
import re
import shlex
import logging
import json
import difflib
import urllib3
import yaml
from jinja2 import Environment, select_autoescape, FileSystemLoader
from kubernetes import client as kube_client
import config
import utils

class MicroService(object):
    '''
    This class is to deploy micro service
    '''
    def __init__(self,service_name,namespace):
        self.service_name = service_name
        self.namespace = namespace
        self.env = self.load_jinja_templates()


#    def set_namespace(self, runtime_env):
#        '''
#        set namespace, with proper postfix
#        '''
#        if namespace == 'kube-system' or runtime_env == 'dev':
#            self.namespace = self.namespace
#        else:
#            self.namespace = self.namespace + '-' + runtime_env



    def load_jinja_templates(self):
        '''
        Load jinja template with relative path
        '''
        workspace = os.environ.get('WORKSPACE')
        if not workspace:
            logging.info('No workspce environment variable')
            logging.info('Use os.cwd, used for development only')
            workspace = os.getcwd()
        logging.info('Current work space %s', workspace)
        logging.debug(self.namespace)
        if self.namespace == 'kube-system':
            manifest_path = os.path.join(workspace,
                                         'kube_manifest_templates',
                                         self.namespace,
                                         self.service_name)
        else:
            manifest_path = os.path.join(workspace,
                                         'kube_manifest_templates',
                                         self.namespace,
                                         self.service_name)
        logging.info('manifest_path, %s', manifest_path)
        loader = FileSystemLoader(manifest_path)
        env = Environment(loader=loader,
                          trim_blocks=False,
                          autoescape=select_autoescape(['xml']))
        logging.debug(env.list_templates())
        return env

    def get_configmap_manifests(self, runtime_env, aws_region):
        '''
        Walk through configmaps dir, use sub dir name as configmap name,
        file name in sub dir as configmap data key name and contents.
        Return: A list of dictionary.
        '''
        configmap_manifests = []
        workspace = os.environ.get('WORKSPACE')
        if not workspace:
            logging.info('No workspce environment variable')
            logging.info('Use os.cwd, used for development only')
            workspace = os.getcwd()
        logging.info('Current work space %s', workspace)
        logging.debug(self.namespace)
        if self.namespace == 'kube-system':
            manifest_path = os.path.join(workspace,
                                         'kube_manifest_templates',
                                         self.namespace,
                                         self.service_name)
        else:
            manifest_path = os.path.join(workspace,
                                         'kube_manifest_templates',
                                         self.namespace.split('-')[0],
                                         self.service_name)
        logging.info('manifest_path, %s', manifest_path)
        config_path = os.path.join(manifest_path, 'configmaps')
        if not os.path.exists(config_path):
            logging.error('%s not exists', config_path)
            return None
        else:
            if self.namespace == 'kube-system' or runtime_env == 'dev':
                namespace = self.namespace
            else:
                namespace = self.namespace + '-' + runtime_env
    
    
            data = {'namespace': namespace,
                    'runtime_env': runtime_env,
                    'aws_region': aws_region}


            for entry in os.scandir(config_path):
                logging.debug('%s in config dir', entry.name)
#                data = self.load_manifest_varibales()
                data['configmap_name'] = entry.name
                data['data'] = {}
                loader = FileSystemLoader(os.path.join(config_path, entry.name))
                env = Environment(loader=loader,
                                  trim_blocks=False,
                                  autoescape=select_autoescape(['xml']))
                for sub_entry in os.scandir(entry.path):
                    template = env.get_template(sub_entry.name)
                    mydata = {'namespace': namespace,
                            'runtime_env': runtime_env,
                            'aws_region': aws_region}
                    body = template.render(data=mydata)
                    if body.strip():
                        data['data'][sub_entry.name[0:-3]] = body.strip()
                template_name = self.service_name + '_' + 'configmap' + '.yaml.j2'
                template = self.env.get_template(template_name)
                manifest = template.render(data=data)
                logging.info(manifest)
                manifest = yaml.load(manifest)
                configmap_manifests.append(manifest)
        #print(configmap_manifests)
        return configmap_manifests

    def load_general_manifest(self, manifest_type, runtime_env, aws_region, extra_vars=None):
        '''
        Load genreral manifest
        Args:
            To add
        Returns:
            Dictionary
        Raises:
            Not implemented yet
        '''
        manifest = ''
        if self.namespace in 'kube-system' or runtime_env == 'dev':
            namespace = self.namespace
        else:
            namespace = self.namespace + '-' + runtime_env


        data = {'namespace': namespace,
                'runtime_env': runtime_env,
                'aws_region': aws_region}

        if extra_vars:
            data['extra_vars'] = extra_vars
#deprecated as no ecr_key need in k8s 1.7
#        if manifest_type == 'ecr':
#            data['ecr_key'] = self.get_ecr_token()
        if manifest_type == 'configmap':
            data['data'] = self.get_configmap_data()
        template_name = self.service_name + '_' + manifest_type + '.yaml.j2'
        template = self.env.get_template(template_name)
        manifest = template.render(data=data)
        logging.info(manifest)
        manifest = yaml.load(manifest)
        #logging.debug(manifest)
        return manifest


#    def api_mapping(self, manifest, action):
#        '''
#        Get api and function name based on action
#        '''
#        func_dict = {
#            'api': '',
#            'name': '',
#            'manifest_type': ''
#        }
#
### Get api name
#        api_version = manifest['apiVersion'].split('/')
#        if api_version[0] == 'v1':
#            func_dict['api'] = 'CoreV1Api'
#            path_prefix = '/api/'
#        else:
#            func_path = '/apis/' + manifest['apiVersion'].lower() + '/'
#            func_tags = utils.deep_get(config.KUBE_SWAGGER,
#                                       'paths',
#                                       func_path,
#                                       'get',
#                                       'tags')
#            logging.info('%s', func_tags[0])
#            for i in func_tags[0].split('_'):
#                func_dict['api'] += i[0].upper() + i[1:]
#            func_dict['api'] += 'Api'
#            path_prefix = '/apis/'
#        namespace = manifest['metadata'].get('namespace', None)
#
### Get func name
#        if namespace:
#            func_path = path_prefix + \
#                        manifest['apiVersion'].lower() + \
#                        '/namespaces/{namespace}/' + \
#                        manifest['kind'].lower() + \
#                        's'
#        else:
#            func_path = path_prefix + \
#                        manifest['apiVersion'].lower() + \
#                        '/' + \
#                        manifest['kind'].lower() + \
#                        's'
#
#        read_func_path = func_path + '/{name}'
#        if action == 'read' or action == 'update':
#            func_path = read_func_path
#
#        logging.debug(func_path)
#        if action == 'create':
#            func_operation = utils.deep_get(config.KUBE_SWAGGER,
#                                            'paths',
#                                            func_path,
#                                            'post',
#                                            'operationId')
#        elif action == 'update':
#            func_operation = utils.deep_get(config.KUBE_SWAGGER,
#                                            'paths',
#                                            func_path,
#                                            'put',
#                                            'operationId')
#        else:
#            func_operation = utils.deep_get(config.KUBE_SWAGGER,
#                                            'paths',
#                                            func_path,
#                                            'get',
#                                            'operationId')
#        logging.info(func_operation)
#        func_dict['name'] = re.sub('([A-Z]+)',
#                                   r'_\1',
#                                   func_operation).lower()
#
### Get manifest_type
#        my_ref = utils.deep_get(config.KUBE_SWAGGER,
#                                'paths',
#                                read_func_path,
#                                'get',
#                                'responses',
#                                '200',
#                                'schema',
#                                '$ref').split('/')[-1]
#        for i in my_ref.split('.'):
#            func_dict['manifest_type'] += i[0].upper() + i[1:]
#        logging.debug(func_dict['manifest_type'])
#        logging.debug(func_dict['api'])
#        logging.debug(func_dict['name'])
#        return func_dict
#
#    def manifest_present(self, manifest):
#        '''
#        Check if manifest present
#        '''
#        #api_func_name = ''.join(i.capitalize() for i in manifest['apiVersion'].split('/')) + \
#        #                'Api'
#        present = False
#        func_dict = self.api_mapping(manifest, 'list')
#        api_func_name, list_func_name = func_dict['api'], func_dict['name']
#        api_instance = getattr(kube_client, api_func_name)(
#            self.cluster_client.api_client)
#        if 'namespace' in manifest['metadata'].keys():
#            existing_list = getattr(api_instance, list_func_name)(
#                manifest['metadata']['namespace']
#            )
#        else:
#            existing_list = getattr(api_instance, list_func_name)()
#        name_list = [x.metadata.name for x in existing_list.items]
#        logging.info(api_func_name)
#        logging.info(list_func_name)
#        logging.debug(existing_list)
#        logging.info(name_list)
#        if manifest['metadata']['name'] not in name_list:
#            logging.info('%s %s not presented',
#                         manifest['kind'],
#                         manifest['metadata']['name'])
#        else:
#            logging.info('%s %s is presented',
#                         manifest['kind'],
#                         manifest['metadata']['name'])
#            present = True
#        return present
#
#    def compare_configmap_data(self, data_a, data_b):
#        '''
#        Check if confimap changed key by key
#        '''
#        changed = False
#        for my_config in set(data_a.keys()).intersection(
#                data_b.keys()
#            ):
#            if data_a[my_config].strip() != data_b[my_config].strip():
#                logging.info('%s does not match that in configmap', my_config)
#                diff_lines = difflib.ndiff(
#                    data_b[my_config].splitlines(1),
#                    data_a[my_config].strip().splitlines(1)
#                    )
#                diff_lines = ''.join(diff_lines)
#                logging.info(diff_lines)
#                changed = True
#            else:
#                logging.info('%s match that in configmap', my_config)
#        for my_config in set(data_b.keys()).difference(
#                data_a.keys()
#            ):
#            logging.warning('%s is not expected, but exists', my_config)
#            changed = True
#        for my_config in set(data_a.keys()).difference(
#                data_b.keys()
#            ):
#            logging.warning('%s is expected, but not', my_config)
#            changed = True
#        return changed
#
#    def diff_yaml(self, yaml_a, yaml_b):
#        '''
#        Pass in two kubernetes manifest spec, and diff them line by line.
#        Ignore None or empty key, it doesn't detect removal of items,
#        For example, if you a has two containers, but b has only one,
#        it returns True.
#        Return: Boolean
#        '''
#        changed = False
#        diff_lines = difflib.ndiff(
#            yaml_a.splitlines(1),
#            yaml_b.splitlines(1)
#            )
#        raw_diff_lines = []
#        filterd_diff_lines = []
#        for i in diff_lines:
#            raw_diff_lines.append(i)
#            if i.strip().endswith('null') and i.strip().startswith('-'):
#                pass
#            elif i.strip().endswith('None') and i.strip().startswith('-'):
#                pass
#            elif i.startswith('?'):
#                pass
#            else:
#                if i.startswith('-') and not i.startswith('-   replicas'):
#                    changed = True
#                    filterd_diff_lines.append(i)
#        logging.debug('Yaml Difference')
#        logging.debug(''.join(raw_diff_lines))
#        logging.debug('Yaml Difference end')
#        if changed:
#            logging.info('Filtered Diff')
#            logging.info(''.join(filterd_diff_lines))
#            logging.info('Filtered Diff ends')
#        return changed
#
#    def manifest_spec_to_yaml(self, manifest_spec):
#        '''
#        Load manifest spec, but it misses those keys we not explictly define,
#        Use k8s python client's desecriablize to complete it, add those empty
#        of none key value pair.
#        Return: Yaml string.
#        '''
#        func_dict = self.api_mapping(manifest_spec, 'read')
#        manifest_type = func_dict['manifest_type']
#        manifest_json = json.dumps(manifest_spec)
#        fake_response = urllib3.response.HTTPResponse(body=manifest_json)
#        manifest_object = self.cluster_client.api_client.deserialize(
#            fake_response,
#            manifest_type)
#        manifest_yaml = yaml.dump(
#            manifest_object.to_dict(),
#            default_flow_style=False)
#        return manifest_yaml
#
#    def get_online_manifest(self, manifest_spec):
#        '''
#        Read in a manifest spec, and get the namespace and name,
#        then fetch online status, for later change check
#        '''
#        func_dict = self.api_mapping(manifest_spec, 'read')
#        api_func_name = func_dict['api']
#        read_func_name = func_dict['name']
#        api_instance = getattr(kube_client, api_func_name)(self.cluster_client.api_client)
#        if 'namespace' in manifest_spec['metadata'].keys():
#            online_manifest = getattr(api_instance, read_func_name)(
#                manifest_spec['metadata']['name'],
#                manifest_spec['metadata']['namespace'])
#        else:
#            online_manifest = getattr(api_instance, read_func_name)(
#                name=manifest_spec['metadata']['name'])
#        logging.debug(online_manifest)
#        return online_manifest
#
#    def manifest_obj_to_yaml(self, manifest_obj):
#        '''
#        After get a online response, we have to transfer it to yaml for comparasion
#        '''
#        manifest_yaml = yaml.dump(
#            manifest_obj.to_dict(),
#            default_flow_style=False)
#        return manifest_yaml
#
#
#    def manifest_changed(self, manifest_spec):
#        '''
#        Read manifest_spec from jinja template,
#        then read relative online status, and compare them to see
#        if there is any change.
#        Return: Boolean
#        '''
#        changed = False
#        online_manifest = self.get_online_manifest(manifest_spec)
#        manifest_spec_yaml = self.manifest_spec_to_yaml(manifest_spec)
#        online_manifest_yaml = self.manifest_obj_to_yaml(online_manifest)
#        if manifest_spec['kind'] == 'ConfigMap':
#            changed = self.compare_configmap_data(
#                data_a=manifest_spec['data'],
#                data_b=online_manifest.data)
#        else:
#            changed = self.diff_yaml(
#                yaml_a=manifest_spec_yaml,
#                yaml_b=online_manifest_yaml)
#        if changed:
#            logging.info('%s %s has changed',
#                         manifest_spec['kind'],
#                         manifest_spec['metadata']['name']
#                        )
#        else:
#            logging.info('%s %s exists and as expected',
#                         manifest_spec['kind'],
#                         manifest_spec['metadata']['name']
#                        )
#        return changed
#
#
#    def create_manifest(self, manifest):
#        '''
#        Create manifest
#        '''
#        created = False
#        func_dict = self.api_mapping(manifest, 'create')
#        api_func_name, create_func_name = func_dict['api'], func_dict['name']
#        api_instance = getattr(kube_client, api_func_name)(
#            self.cluster_client.api_client)
#        logging.info(create_func_name)
#        if 'namespace' not in manifest['metadata']:
#            create_result = getattr(api_instance, create_func_name)(
#                body=manifest)
#        else:
#            create_result = getattr(api_instance, create_func_name)(
#                manifest['metadata']['namespace'], body=manifest)
#        logging.debug(create_result)
#        return created
#
#    def update_manifest(self, manifest):
#        '''
#        Replace k8s object
#        '''
#        replaced = False
#        func_dict = self.api_mapping(manifest, 'update')
#        api_func_name, replace_func_name = func_dict['api'], func_dict['name']
#        api_instance = getattr(kube_client, api_func_name)(
#            self.cluster_client.api_client)
#        logging.info(replace_func_name)
#        if 'namespace' not in manifest['metadata']:
#            replace_result = getattr(api_instance, replace_func_name)(
#                manifest['metadata']['name'], body=manifest)
#        else:
#            replace_result = getattr(api_instance, replace_func_name)(
#                manifest['metadata']['name'],
#                manifest['metadata']['namespace'],
#                body=manifest)
#        logging.debug(replace_result)
#        return replaced
#
#    def list_images(self, manifest):
#        '''
#        List images used by manifest in deployment or ds
#        '''
#        images_list = []
#        logging.info("Manifest type: %s", manifest['kind'])
#        containers = utils.deep_get(manifest,
#                                    'spec',
#                                    'template',
#                                    'spec',
#                                    'containers')
#        for container in containers:
#            logging.info('container images: %s', container['image'])
#            images_list.append(container['image'])
#
#        init_containers = utils.deep_get(manifest,
#                                         'spec',
#                                         'template',
#                                         'spec',
#                                         'initContainers')
#        for container in init_containers:
#            logging.info('init container images: %s', container['image'])
#            images_list.append(container['image'])
#
#
#    def list_pods(self):
#        '''
#        list pods in namespace
#        '''
#        api_instance = getattr(kube_client, 'CoreV1Api')(
#            self.cluster_client.api_client)
#        existing_pods = getattr(api_instance, 'list_namespaced_pod')(
#            self.namespace)
#        pod_list = []
#        for pod in existing_pods.items:
#            logging.info(pod.metadata.name)
#            pod_list.append(pod.metadata.name)
#        return pod_list
#
#
#    def get_logs(self, container, tail_lines=1):
#        '''
#        Get k8s log
#        '''
#        pod_list = self.list_pods()
#        api_instance = getattr(kube_client, 'CoreV1Api')(
#            self.cluster_client.api_client)
#        for pod_name in pod_list:
#            logging.info(pod_name)
#            filtered_logs = getattr(api_instance, 'read_namespaced_pod_log')(
#                pod_name,
#                self.namespace,
#                container=container,
#                tail_lines=tail_lines)
#            logging.info(filtered_logs)
#
#    def exec_command(self, pod_name, container, command):
#        '''
#        exec command in pod
#        '''
#        command = shlex.split(command)
#        print(command)
#        print(self.cluster_client.api_client.config)
#        self.cluster_client.api_client.config.verify_ssl = False
#        api_instance = getattr(kube_client, 'CoreV1Api')(
#            self.cluster_client.api_client)
#        logging.info(pod_name)
#        response = getattr(api_instance, 'connect_get_namespaced_pod_exec')(
#            pod_name,
#            self.namespace,
#            command=command,
#            container=container,
#            stderr=True,
#            stdin=False,
#            stdout=True,
#            tty=False)
#        logging.info(response)
#
#
#    def deploy_manifest(self, manifest, dry_run=True):
#        '''
#        Deploy manifest, check exists first
#        '''
#        deployed = False
#        if self.manifest_present(manifest):
#            if self.manifest_changed(manifest):
#                if dry_run:
#                    logging.warning('Dry run, skip updating')
#                else:
#                    logging.warning('Updating')
#                    self.update_manifest(manifest)
#            else:
#                logging.warning('No Change, No Update!')
#                deployed = True
#        else:
#            if dry_run:
#                logging.warning('Dry run, skip creation')
#            else:
#                logging.warning('Creating')
#                self.create_manifest(manifest)
#        return deployed
#        self.loader = ''
#        self.env = ''

#
#    def set_cluster_client(self,
#                           aws_region='',
#                           runtime_env='',
#                           dry_run=True):
#        '''
#        Set cluster client based on env and region
#        '''
#        self.cluster_client = ClusterClient(aws_region, runtime_env, dry_run)
#Deprecated as no ecr_key needed in k8s 1.7
#    def load_ecr_key_manifest(self):
#        '''
#        Load ecr key manifest
#        '''
#        auth_token = self.get_ecr_token()
#        data = {'namespace': self.namespace,
#                'ecr_key': auth_token}
#        template_name = 'ecr_key_secret.yaml.j2'
#        logging.debug('List templates')
#        logging.debug(self.env.list_templates())
#        template = self.env.get_template(template_name)
#        body = template.render(data=data)
#        body = yaml.load(body)
#        logging.info('Ecr key manifest')
#        logging.debug(body)
#        return body

##Deprecated as no ecr key need in k8s 1.7
#    def get_ecr_token(self):
#        '''
#        Get ecr token
#        '''
#        auth_token = ''
#        if self.cluster_client.runtime_env in ['test', 'dev', 'stage']:
#            ecr_client = self.cluster_client.aws_session.client('ecr')
#            response = ecr_client.get_authorization_token(
#                registryIds=[
#                    '111111111111'
#                ]
#            )
#        elif self.cluster_client.runtime_env in ['prod']:
#            ecr_client = self.cluster_client.aws_session.client('ecr')
#            response = ecr_client.get_authorization_token(
#                registryIds=[
#                    '222222222222'
#                ]
#            )
#        else:
#            logging.error('Unsupported runtime env')
#        logging.debug(response)
#        if response:
#            auth_token = response['authorizationData'][0]['authorizationToken']
#            proxy_endpoint = response['authorizationData'][0]['proxyEndpoint']
#            auth_token = {
#                "auths": {
#                    proxy_endpoint : {
#                        'auth' : auth_token
#                    }
#                }
#            }
#            auth_token = base64.b64encode(json.dumps(auth_token).encode())
#            auth_token = auth_token.decode()
#            logging.debug(auth_token)
#        return auth_token

#Deprecated, use compare_configmap_data instead
#    def configmap_changed(self, configmap_data, api_response):
#        '''
#        Check if confimap changed key by key
#        '''
#        changed = False
#        for my_config in set(api_response.data.keys()).intersection(
#                configmap_data.keys()
#            ):
#            if configmap_data[my_config].strip() != api_response.data[my_config].strip():
#                logging.info('%s does not match that in configmap', my_config)
#                diff_lines = difflib.ndiff(
#                    api_response.data[my_config].splitlines(1),
#                    configmap_data[my_config].strip().splitlines(1)
#                    )
#                diff_lines = ''.join(diff_lines)
#                logging.info(diff_lines)
#                changed = True
#            else:
#                logging.info('%s match that in configmap', my_config)
#        for my_config in set(api_response.data.keys()).difference(
#                configmap_data.keys()
#            ):
#            logging.warning('%s is not expected, but exists', my_config)
#            changed = True
#        for my_config in set(configmap_data.keys()).difference(
#                api_response.data.keys()
#            ):
#            logging.warning('%s is expected, but not', my_config)
#            changed = True
#        return changed

#    def get_configmap_variables(self, runtime_env, aws_region):
#        '''
#        Configmap might have its own variable
#        '''
#        config_variables = {}
#        config_variables['runtime_env'] = runtime_env
#        config_variables['aws_region'] = aws_region
#        return config_variables
#
#Deprecated use sub dir for configmap now
#    def get_configmap_data(self):
#        '''
#        compose configmap with file in config directory
#        '''
#        config_data = {}
#        for i in self.env.list_templates():
#            if i.startswith('config/'):
#                config_variables = self.get_configmap_variables()
#                config_name = i.split('/')[-1][0:-3]
#                template = self.env.get_template(i)
#                body = template.render(data=config_variables)
#                if self.cluster_client.runtime_env in ['dev', 'stage']:
#                    key_name = config_name # + '.tmpl'
#                    config_data[key_name] = body
#                else:
#                    config_data[config_name] = body
#        logging.debug(config_data)
#        return config_data

#Set elk env in template but not in script
#    def get_elk_env(self):
#        '''
#        Get elk variables for logstash
#        '''
#        elk_redis_aws_region = self.cluster_client.aws_region
#        if self.cluster_client.runtime_env == 'prod':
#            elk_redis_env = self.cluster_client.runtime_env
#        elif self.cluster_client.runtime_env in ['dev', 'stage', 'test']:
#            elk_redis_env = 'stage'
#        else:
#            logging.error('Unsupported env %s', self.cluster_client.runtime_env)
#            logging.error('Fail to set elk env varibales')
#            elk_redis_env = ''
#        return (elk_redis_aws_region, elk_redis_env)

#Use load_general_manifest, deprecated
#    def load_deploy_manifest(self, image_url):
#        '''
#        Load deploy manifest from template
#        '''
#        deploy_manifest = ''
#        (elk_redis_aws_region, elk_redis_env) = self.get_elk_env()
#        template_name = self.service_name + '_deploy.yaml.j2'
#        template = self.env.get_template(template_name)
#        deploy_manifest = template.render(
#            namespace=self.namespace,
#            runtime_env=self.cluster_client.runtime_env,
#            elk_redis_env=elk_redis_env,
#            elk_redis_aws_region=elk_redis_aws_region,
#            image_url=image_url
#            )
#        deploy_manifest = yaml.load(deploy_manifest)
#        logging.debug(deploy_manifest)
#        return deploy_manifest

##image check should limited to specific project, just as 
##
#    def image_exists(self, repo_name, image_tag):
#        '''
#        Check if image exists in ecr
#        '''
#        ecr_client = self.cluster_client.aws_session.client('ecr')
#        try:
#            response = ecr_client.describe_images(
#                repositoryName=repo_name,
#                imageIds=[{'imageTag':image_tag}])
#            logging.debug('image info: %s', response)
#            return True
#        except ecr_client.exceptions.ImageNotFoundException as image_error:
#            logging.error('image %s not found in repo %s', image_tag, repo_name)
#            logging.error('Error info: %s', str(image_error))
#            raise
#        return False
#
#    def get_image_url(self,
#                      image_tag):
#        '''
#        Get image url
#        '''
#        image_url = ''
#        repo_name = self.namespace.split('-')[0] + \
#                          '-' + \
#                          self.service_name
#        image_url = '111111111111.dkr.ecr.us-east-1.amazonaws.com/' + \
#                    self.namespace.split('-')[0] + \
#                    '-' + \
#                    self.service_name + \
#                    ':' + \
#                    image_tag
#        if self.image_exists(repo_name, image_tag):
#            pass
#        else:
#            image_url = None
#        return image_url


#    def load_manifest_varibales(self, runtime_env, aws_region):
#        '''
#        Load manifest varibales
#        '''
#        data = {'namespace': self.namespace,
#                'runtime_env': runtime_env,
#                'aws_region': aws_region}
#        return data


