#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for alexrhino sample_application service
"""

import sys
import logging
import boto3
import json
import fire
import config
from cluster_manager import ClusterManager
from sample_application import SampleApplication

def main(min_replica=1,
         max_replica=2,
         aws_region='vir',
         runtime_env='dev',
         dry_run=True,
         debug=True):
    '''
    Main function
    '''
    service_name='sample_application'
    namespace='alexrhino'
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.info("DEBUG ON")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("DEBUG OFF")
    if int(max_replica) >= int(min_replica) and int(min_replica) > 0:
        cm = ClusterManager(runtime_env, aws_region)
        my_service = SampleApplication('sample_application', 'alexrhino')
        manifest_spec = my_service.load_general_manifest('hpa', runtime_env, aws_region)
        manifest_spec['spec']['maxReplicas'] = max_replica 
        manifest_spec['spec']['minReplicas'] = min_replica 
        cm.deploy_manifest(manifest_spec, dry_run)
    else:
        logging.error('Wrong replica range, from %s to %s, please check', min_replica, max_replica)
if __name__ == '__main__':
    fire.Fire(main)
