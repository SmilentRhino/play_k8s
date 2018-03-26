#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for alexrhino sample service
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
from kubernetes import client as kube_client, config as kube_config
import config
import utils
from micro_service import MicroService
from sample_application import SampleApplication

class ClusterManager(object):
    '''
    This class is to deploy micro service
    '''
    def __init__(self, runtime_env, aws_region):
        config_file_path = '/home/ubuntu/.kube/config_new_' + runtime_env
        logging.info('Load kubectl from %s', config_file_path)
        self.context = config.KUBE_CONTEXTS[runtime_env][aws_region]['context']
        logging.info('Kubectl context is %s', self.context)
        logging.info('Get kube client for %s in %s',
                     aws_region,
                     runtime_env)
        self.manifests = config.KUBE_CONTEXTS[runtime_env][aws_region]['manifests'] 
        self.api_client = kube_config.new_client_from_config(
            config_file=config_file_path,
            context=self.context)
        self.runtime_env = runtime_env
        self.aws_region = aws_region

    def api_mapping(self, manifest, action):
        '''
        Get api and function name based on action
        '''
        func_dict = {
            'api': '',
            'name': '',
            'manifest_type': ''
        }

## Get api name
        api_version = manifest['apiVersion'].split('/')
        if api_version[0] == 'v1':
            func_dict['api'] = 'CoreV1Api'
            path_prefix = '/api/'
        else:
            func_path = '/apis/' + manifest['apiVersion'].lower() + '/'
            func_tags = utils.deep_get(config.KUBE_SWAGGER,
                                       'paths',
                                       func_path,
                                       'get',
                                       'tags')
            logging.info('%s', func_tags[0])
            for i in func_tags[0].split('_'):
                func_dict['api'] += i[0].upper() + i[1:]
            func_dict['api'] += 'Api'
            path_prefix = '/apis/'
        namespace = manifest['metadata'].get('namespace', None)

## Get func name
        if namespace:
            func_path = path_prefix + \
                        manifest['apiVersion'].lower() + \
                        '/namespaces/{namespace}/' + \
                        manifest['kind'].lower() + \
                        's'
        else:
            func_path = path_prefix + \
                        manifest['apiVersion'].lower() + \
                        '/' + \
                        manifest['kind'].lower() + \
                        's'

        read_func_path = func_path + '/{name}'
        if action == 'read' or action == 'update':
            func_path = read_func_path

        logging.debug(func_path)
        if action == 'create':
            func_operation = utils.deep_get(config.KUBE_SWAGGER,
                                            'paths',
                                            func_path,
                                            'post',
                                            'operationId')
        elif action == 'update':
            func_operation = utils.deep_get(config.KUBE_SWAGGER,
                                            'paths',
                                            func_path,
                                            'put',
                                            'operationId')
        else:
            func_operation = utils.deep_get(config.KUBE_SWAGGER,
                                            'paths',
                                            func_path,
                                            'get',
                                            'operationId')
        logging.info(func_operation)
        func_dict['name'] = re.sub('([A-Z]+)',
                                   r'_\1',
                                   func_operation).lower()
## Get manifest_type
        my_ref = utils.deep_get(config.KUBE_SWAGGER,
                                'paths',
                                read_func_path,
                                'get',
                                'responses',
                                '200',
                                'schema',
                                '$ref').split('/')[-1]
        for i in my_ref.split('.'):
            func_dict['manifest_type'] += i[0].upper() + i[1:]
        logging.debug(func_dict['manifest_type'])
        logging.debug(func_dict['api'])
        logging.debug(func_dict['name'])
        return func_dict


    def manifest_present(self, manifest):
        '''
        Check if manifest present
        '''
        #api_func_name = ''.join(i.capitalize() for i in manifest['apiVersion'].split('/')) + \
        #                'Api'
        present = False
        func_dict = self.api_mapping(manifest, 'list')
        api_func_name, list_func_name = func_dict['api'], func_dict['name']
        api_instance = getattr(kube_client, api_func_name)(
            self.api_client)
        if 'namespace' in manifest['metadata'].keys():
            existing_list = getattr(api_instance, list_func_name)(
                manifest['metadata']['namespace']
            )
        else:
            existing_list = getattr(api_instance, list_func_name)()
        name_list = [x.metadata.name for x in existing_list.items]
        logging.info(api_func_name)
        logging.info(list_func_name)
        logging.debug(existing_list)
        logging.info(name_list)
        if manifest['metadata']['name'] not in name_list:
            logging.info('%s %s not presented',
                         manifest['kind'],
                         manifest['metadata']['name'])
        else:
            logging.info('%s %s is presented',
                         manifest['kind'],
                         manifest['metadata']['name'])
            present = True
        return present

    def compare_configmap_data(self, data_a, data_b):
        '''
        Check if confimap changed key by key
        '''
        changed = False
        for my_config in set(data_a.keys()).intersection(
                data_b.keys()
            ):
            if data_a[my_config].strip() != data_b[my_config].strip():
                logging.info('%s does not match that in configmap', my_config)
                diff_lines = difflib.ndiff(
                    data_b[my_config].splitlines(1),
                    data_a[my_config].strip().splitlines(1)
                    )
                diff_lines = ''.join(diff_lines)
                logging.info(diff_lines)
                changed = True
            else:
                logging.info('%s match that in configmap', my_config)
        for my_config in set(data_b.keys()).difference(
                data_a.keys()
            ):
            logging.warning('%s is not expected, but exists', my_config)
            changed = True
        for my_config in set(data_a.keys()).difference(
                data_b.keys()
            ):
            logging.warning('%s is expected, but not', my_config)
            changed = True
        return changed

    def diff_yaml(self, yaml_a, yaml_b):
        '''
        Pass in two kubernetes manifest spec, and diff them line by line.
        Ignore None or empty key, it doesn't detect removal of items,
        For example, if you a has two containers, but b has only one,
        it returns True.
        Return: Boolean
        '''
        changed = False
        diff_lines = difflib.ndiff(
            yaml_a.splitlines(1),
            yaml_b.splitlines(1)
            )
        raw_diff_lines = []
        filterd_diff_lines = []
        for i in diff_lines:
            raw_diff_lines.append(i)
            if i.strip().endswith('null') and i.strip().startswith('-'):
                pass
            elif i.strip().endswith('None') and i.strip().startswith('-'):
                pass
            elif i.startswith('?'):
                pass
            else:
                if i.startswith('-') and not i.startswith('-   replicas'):
                    changed = True
                    filterd_diff_lines.append(i)
        logging.debug('Yaml Difference')
        logging.debug(''.join(raw_diff_lines))
        logging.debug('Yaml Difference end')
        if changed:
            logging.info('Filtered Diff')
            logging.info(''.join(filterd_diff_lines))
            logging.info('Filtered Diff ends')
        return changed

    def manifest_spec_to_yaml(self, manifest_spec):
        '''
        Load manifest spec, but it misses those keys we not explictly define,
        Use k8s python client's desecriablize to complete it, add those empty
        of none key value pair.
        Return: Yaml string.
        '''
        func_dict = self.api_mapping(manifest_spec, 'read')
        manifest_type = func_dict['manifest_type']
        manifest_json = json.dumps(manifest_spec)
        fake_response = urllib3.response.HTTPResponse(body=manifest_json)
        manifest_object = self.api_client.deserialize(
            fake_response,
            manifest_type)
        manifest_yaml = yaml.dump(
            manifest_object.to_dict(),
            default_flow_style=False)
        return manifest_yaml

    def get_online_manifest(self, manifest_spec):
        '''
        Read in a manifest spec, and get the namespace and name,
        then fetch online status, for later change check
        '''
        func_dict = self.api_mapping(manifest_spec, 'read')
        api_func_name = func_dict['api']
        read_func_name = func_dict['name']
        api_instance = getattr(kube_client, api_func_name)(self.api_client)
        if 'namespace' in manifest_spec['metadata'].keys():
            online_manifest = getattr(api_instance, read_func_name)(
                manifest_spec['metadata']['name'],
                manifest_spec['metadata']['namespace'])
        else:
            online_manifest = getattr(api_instance, read_func_name)(
                name=manifest_spec['metadata']['name'])
        logging.debug(online_manifest)
        return online_manifest

    def manifest_obj_to_yaml(self, manifest_obj):
        '''
        After get a online response, we have to transfer it to yaml for comparasion
        '''
        manifest_yaml = yaml.dump(
            manifest_obj.to_dict(),
            default_flow_style=False)
        return manifest_yaml


    def manifest_changed(self, manifest_spec):
        '''
        Read manifest_spec from jinja template,
        then read relative online status, and compare them to see
        if there is any change.
        Return: Boolean
        '''
        changed = False
        online_manifest = self.get_online_manifest(manifest_spec)
        manifest_spec_yaml = self.manifest_spec_to_yaml(manifest_spec)
        online_manifest_yaml = self.manifest_obj_to_yaml(online_manifest)
        if manifest_spec['kind'] == 'ConfigMap':
            changed = self.compare_configmap_data(
                data_a=manifest_spec['data'],
                data_b=online_manifest.data)
        else:
            changed = self.diff_yaml(
                yaml_a=manifest_spec_yaml,
                yaml_b=online_manifest_yaml)
        if changed:
            logging.info('%s %s has changed',
                         manifest_spec['kind'],
                         manifest_spec['metadata']['name']
                        )
        else:
            logging.info('%s %s exists and as expected',
                         manifest_spec['kind'],
                         manifest_spec['metadata']['name']
                        )
        return changed


    def create_manifest(self, manifest):
        '''
        Create manifest
        '''
        created = False
        func_dict = self.api_mapping(manifest, 'create')
        api_func_name, create_func_name = func_dict['api'], func_dict['name']
        api_instance = getattr(kube_client, api_func_name)(
            self.api_client)
        logging.info(create_func_name)
        if 'namespace' not in manifest['metadata']:
            create_result = getattr(api_instance, create_func_name)(
                body=manifest)
        else:
            create_result = getattr(api_instance, create_func_name)(
                manifest['metadata']['namespace'], body=manifest)
        logging.debug(create_result)
        return created

    def update_manifest(self, manifest):
        '''
        Replace k8s object
        '''
        replaced = False
        func_dict = self.api_mapping(manifest, 'update')
        api_func_name, replace_func_name = func_dict['api'], func_dict['name']
        api_instance = getattr(kube_client, api_func_name)(
            self.api_client)
        logging.info(replace_func_name)
        if 'namespace' not in manifest['metadata']:
            replace_result = getattr(api_instance, replace_func_name)(
                manifest['metadata']['name'], body=manifest)
        else:
            replace_result = getattr(api_instance, replace_func_name)(
                manifest['metadata']['name'],
                manifest['metadata']['namespace'],
                body=manifest)
        logging.debug(replace_result)
        return replaced

    def list_images(self, manifest):
        '''
        List images used by manifest in deployment or ds
        '''
        images_list = []
        logging.info("Manifest type: %s", manifest['kind'])
        containers = utils.deep_get(manifest,
                                    'spec',
                                    'template',
                                    'spec',
                                    'containers')
        for container in containers:
            logging.info('container images: %s', container['image'])
            images_list.append(container['image'])

        init_containers = utils.deep_get(manifest,
                                         'spec',
                                         'template',
                                         'spec',
                                         'initContainers')
        for container in init_containers:
            logging.info('init container images: %s', container['image'])
            images_list.append(container['image'])


    def list_pods(self, namespace):
        '''
        list pods in namespace
        '''
        api_instance = getattr(kube_client, 'CoreV1Api')(
            self.api_client)
        existing_pods = getattr(api_instance, 'list_namespaced_pod')(
            namespace)
        pod_list = []
        if existing_pods.items:
            logging.info('Following pods exists:')
            for pod in existing_pods.items:
                logging.info(pod.metadata.name)
                pod_list.append(pod.metadata.name)
            logging.info('Ends')
        else:
            logging.info('No pod found.')
        return pod_list


    def get_logs(self, namespace, container, tail_lines=1):
        '''
        Get k8s log
        '''
        pod_list = self.list_pods(namespace)
        api_instance = getattr(kube_client, 'CoreV1Api')(
            self.api_client)
        for pod_name in pod_list:
            logging.info(pod_name)
            filtered_logs = getattr(api_instance, 'read_namespaced_pod_log')(
                pod_name,
                namespace,
                container=container,
                tail_lines=tail_lines)
            logging.info(filtered_logs)

    def exec_command(self, namespace, pod_name, container, command):
        '''
        exec command in pod
        '''
        command = shlex.split(command)
        print(command)
        print(self.api_client.config)
        self.api_client.config.verify_ssl = False
        api_instance = getattr(kube_client, 'CoreV1Api')(
            self.api_client)
        logging.info(pod_name)
        response = getattr(api_instance, 'connect_get_namespaced_pod_exec')(
            pod_name,
            namespace,
            command=command,
            container=container,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False)
        logging.info(response)


    def deploy_manifest(self, manifest, dry_run=True):
        '''
        Deploy manifest, check exists first
        '''
        deployed = False
        if self.manifest_present(manifest):
            if self.manifest_changed(manifest):
                if dry_run:
                    logging.warning('Dry run, skip updating')
                else:
                    logging.warning('Updating')
                    self.update_manifest(manifest)
            else:
                logging.warning('No Change, No Update!')
                deployed = True
        else:
            if dry_run:
                logging.warning('Dry run, skip creation')
            else:
                logging.warning('Creating')
                self.create_manifest(manifest)
        return deployed

    def export(self, root_dir):
        for manifest in self.manifests:
            for service in manifest['services']:
                if service['service'] == 'sample_application':
                    my_service = PushNotification(service['service'], manifest['namespace'])
                else:
                    my_service = MicroService(service['service'], manifest['namespace'])
                for my_type in service['type']:
                    if my_type == 'configmap':
                        manifest_specs = my_service.get_configmap_manifests(self.runtime_env, self.aws_region)
                        for manifest_obj in manifest_specs:
                            namespace_path = manifest_obj['metadata'].get('namespace')
                            if namespace_path:
                                file_path = root_dir + '/' + '/'.join([self.context, namespace_path, manifest_obj['metadata'].get('name') + '_' +manifest_obj['kind']])
                            else:
                                file_path = root_dir + '/' + '/'.join([self.context, manifest_obj['metadata'].get('name') + '_' +manifest_obj['kind']])
                            file_path = file_path.lower() + '.yaml'
                            dir_path, file_name = os.path.split(file_path)
                            logging.info(dir_path)
                            if os.path.exists(dir_path):
                                logging.info('Path exists')
                            else:
                                logging.info('Path not exists')
                                os.makedirs(dir_path)
                            with open(file_path,'w') as f:
                                yaml.dump(manifest_obj, f, default_flow_style=False)
                    else:
                        manifest_obj = my_service.load_general_manifest(my_type, self.runtime_env, self.aws_region)
                        namespace_path = manifest_obj['metadata'].get('namespace')
                        if namespace_path:
                            file_path = root_dir + '/' + '/'.join([self.context, namespace_path, manifest_obj['metadata'].get('name') + '_' +manifest_obj['kind']])
                        else:
                            file_path = root_dir + '/' + '/'.join([self.context, manifest_obj['metadata'].get('name') + '_' +manifest_obj['kind']])
                        file_path = file_path.lower() + '.yaml'
                        dir_path, file_name = os.path.split(file_path)
                        logging.info(dir_path)
                        if os.path.exists(dir_path):
                            logging.info('Path exists')
                        else:
                            logging.info('Path not exists')
                            os.makedirs(dir_path)
                        with open(file_path,'w') as f:
                            yaml.dump(manifest_obj, f, default_flow_style=False)

                     


    def validate(self):
        result = { 'status': True, 'changed_list': []} 
        changed_manifests = []
        all_manifest_specs = []
        for manifest in self.manifests:
            for service in manifest['services']:
                if service['service'] == 'sample_application':
                    my_service = PushNotification(service['service'], manifest['namespace'])
                else:
                    my_service = MicroService(service['service'], manifest['namespace'])
                for my_type in service['type']:
                    if my_type == 'configmap':
                        manifest_spec = my_service.get_configmap_manifests(self.runtime_env, self.aws_region)
                        all_manifest_specs.extend(manifest_spec)
                    else:
                        manifest_spec = my_service.load_general_manifest(my_type, self.runtime_env, self.aws_region)
                        all_manifest_specs.append(manifest_spec)
        for manifest_spec in all_manifest_specs:
            deployed = self.deploy_manifest(manifest_spec, dry_run=True) 
            if not deployed:
                changed_manifests.append(manifest_spec)
        if changed_manifests:
            logging.warning('Oops, changes detected!')
            for manifest in changed_manifests:
                logging.warning('%s %s in %s has changed, please check!', manifest['kind'], manifest['metadata']['name'], manifest['metadata'].get('namespace', None))
                result['changed_list'].append([manifest['kind'], manifest['metadata']['name'], manifest['metadata'].get('namespace', None)])
            logging.warning('Changed end!')
            result['status'] = False
        else:
            logging.info('Congratulations! All as expected!!!')
        return result
