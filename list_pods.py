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
from cluster_manager import ClusterManager

def main(aws_region='vir',
         runtime_env='dev',
         debug=False):
    '''
    Main function
    '''
    service_name='sample_application'
    if runtime_env == 'dev':
        namespace='alexrhino'
    else:
        namespace='alexrhino-' + runtime_env
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.info("DEBUG ON")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("DEBUG OFF")
    cm = ClusterManager(runtime_env, aws_region)
    cm.list_pods(namespace)

if __name__ == '__main__':
    fire.Fire(main)
