#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for sample_application service
"""

import logging
import fire
from micro_service import MicroService
from cluster_manager import ClusterManager

def main(pod_name,
         container,
         aws_region='vir',
         runtime_env='dev',
         namespace='alexrhino',
         command='date',
         debug=False):
    '''
    Main function
    '''
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.info("DEBUG ON")
    else:
        logging.basicConfig(level=logging.INFO)
        logging.info("DEBUG OFF")
    cm = ClusterManager(runtime_env, aws_region)
    cm.exec_command(namespace, pod_name, container, command)

if __name__ == '__main__':
    fire.Fire(main)
