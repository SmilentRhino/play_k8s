#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for alexrhino sample_application service
"""

import sys
import logging
import fire
import config
from cluster_manager import ClusterManager
from micro_service import MicroService

def main(service_name='sample_application',
         aws_region='tyo',
         runtime_env='test',
         dry_run=True,
         namespace='alexrhino',
         debug=True,
         extra_vars='',
         manifest_type='configmap'):
    '''
    Main function
    '''
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.info("DEBUG ON")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("DEBUG OFF")
    cluster_controller = ClusterManager(runtime_env, aws_region)
    general_service = MicroService(service_name, namespace)
    if manifest_type == 'configmap':
        manifests = general_service.get_configmap_manifests(runtime_env, aws_region)
    else:
        manifest = general_service.load_general_manifest(manifest_type, runtime_env, aws_region, extra_vars)
        manifests = [ manifest ]
    for manifest in manifests:
        cluster_controller.deploy_manifest(manifest, dry_run)

if __name__ == '__main__':
    fire.Fire(main)
