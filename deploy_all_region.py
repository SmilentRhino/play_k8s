#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for  sample_application service
"""
import sys
import logging
import fire
import config
from micro_service import MicroService
from sample_application import SampleApplication
from cluster_manager import ClusterManager


def set_log_level(debug):
    '''
    Show debug info or not
    '''
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.info("DEBUG ON")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("DEBUG OFF")

def deploy_all_regions(runtime_env,
                       namespace,
                       service_name,
                       manifest_type,
                       dry_run=True,
                       debug=True):
    '''
    Main function
    '''
    set_log_level(debug)
    all_changed = []
    runtime_envs = config.get_runtime_envs(runtime_env)
    if service_name == 'sample_application':
        my_service = SampleApplication(service_name, namespace)
    else:
        my_service = MicroService(service_name, namespace)
    for env in runtime_envs:
        for region in config.get_regions(env, 'all'):
            cm = ClusterManager(env, region)
            if config.has_manifest(env, region, namespace, service_name, manifest_type):
                manifest_spec = my_service.load_general_manifest(manifest_type, runtime_env, region)
                cm.deploy_manifest(manifest_spec, dry_run)
    
if __name__ == '__main__':
    fire.Fire(deploy_all_regions)
