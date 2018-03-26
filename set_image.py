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

def main(image_tag,
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
    cm = ClusterManager(runtime_env, aws_region)
    my_service = SampleApplication('sample_application', 'alexrhino')
    image_url = my_service.get_image_url(image_tag)
    extra_vars = {'image_url': image_url}
    manifest_spec = my_service.load_general_manifest('deploy', runtime_env, aws_region, extra_vars=extra_vars)
    if not dry_run:
        my_service.update_s3_image_url(runtime_env, aws_region, image_tag)
    cm.deploy_manifest(manifest_spec, dry_run)
if __name__ == '__main__':
    fire.Fire(main)
