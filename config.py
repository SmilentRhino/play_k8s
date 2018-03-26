#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Load config
"""

import json
import yaml


KUBE_CONTEXTS = {}
KUBE_SWAGGER = ''
with open('swagger.json', 'r') as f:
    KUBE_SWAGGER = json.load(f)

with open('cluster_spec/cluster_info.yaml', 'r') as f:
    KUBE_CONTEXTS = yaml.load(f)

def get_runtime_envs(runtime_env):
    runtime_envs = [] 
    if runtime_env == 'all':
        runtime_envs = KUBE_CONTEXTS.keys()
    else:
        runtime_envs.append(runtime_env)
    return runtime_envs

def get_regions(env, aws_region):
    regions = []
    if aws_region == 'all':
        regions = KUBE_CONTEXTS[env].keys()
    else:
        regions.append(aws_region)
    return regions 

def has_manifest(env, aws_region, namespace, service_name, manifest_type):
    for manifest in KUBE_CONTEXTS[env][aws_region]['manifests']:
        if namespace == manifest['namespace']:
             for service in manifest['services']:
                 if service_name == service['service']:
                      if manifest_type in service['type']:
                          return True
    return False
