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

def main(aws_region='vir',
         runtime_env='dev',
         debug=False):
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
    cm = ClusterManager(runtime_env, aws_region)
    sample_application_service = SampleApplication('sample_application','alexrhino')
    manifest_spec = sample_application_service.load_general_manifest('deploy', runtime_env, aws_region)
    cm.list_images(manifest_spec)
if __name__ == '__main__':
    fire.Fire(main)
