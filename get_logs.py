#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for alexrhino sample_application service
"""

import logging
import fire
from cluster_manager import ClusterManager

def main(aws_region='fra',
         runtime_env='test',
         namespace='alexrhino',
         debug=True,
         container='sample_application-service-log',
         tail_lines=1):
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
    cm.get_logs(namespace, container, tail_lines)

if __name__ == '__main__':
    fire.Fire(main)
