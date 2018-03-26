#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The bootstrap and deploy script for alexrhino sample service
"""

import sys
import logging
import boto3
import fire
import config
from micro_service import MicroService

class SampleApplication(MicroService):

    def image_exists(self, repo_name, image_tag):
        '''
        Check if image exists in ecr
        '''
        aws_session = boto3.Session(profile_name='alexrhino-dev')
        ecr_client = aws_session.client('ecr')
        try:
            response = ecr_client.describe_images(
                repositoryName=repo_name,
                imageIds=[{'imageTag':image_tag}])
            logging.debug('image info: %s', response)
            return True
        except ecr_client.exceptions.ImageNotFoundException as image_error:
            logging.error('image %s not found in repo %s', image_tag, repo_name)
            logging.error('Error info: %s', str(image_error))
            raise
        return False

    def get_image_url(self,
                      image_tag):
        '''
        Get image url
        '''
        image_url = ''
        repo_name = self.namespace.split('-')[0] + \
                          '-' + \
                          self.service_name
        image_url = '111111111111.dkr.ecr.us-east-1.amazonaws.com/' + \
                    self.namespace.split('-')[0] + \
                    '-' + \
                    self.service_name + \
                    ':' + \
                    image_tag
        if self.image_exists(repo_name, image_tag):
            pass
        else:
            image_url = None
        return image_url

    def get_s3_image_url(self, runtime_env, aws_region):
        image_url = ''
        key_name = runtime_env + '/' + aws_region + '/'+ 'image_url'
        logging.info('Fetch %s in bucket %s', key_name, 'alexrhino-sample-deployment')
        aws_session = boto3.Session(profile_name='alexrhino-dev')
        s3_client = aws_session.client('s3')
        resp = s3_client.get_object(Bucket='alexrhino-sample-deployment',Key=key_name)
        image_url = resp['Body'].read().decode()
        logging.debug('image_url is %s', image_url)
        return image_url

    def update_s3_image_url(self, runtime_env, aws_region, image_tag):
        updated = False
        key_name = runtime_env + '/' + aws_region + '/'+ 'image_url'
        image_url = self.get_image_url(image_tag)
        if image_url:
            logging.info('Update %s in bucket %s', key_name, 'alexrhino-sample-deployment')
            aws_session = boto3.Session(profile_name='alexrhino-dev')
            s3_client = aws_session.client('s3')
            resp = s3_client.put_object(Bucket='alexrhino-sample-deployment',Key=key_name, Body=image_url)
            if resp['ResponseMetadata']['HTTPStatusCode'] == 200:
                logging.info('Update succeed')
                updated = True
        return updated
#
#    def load_deploy_manifest(self, image_tag=None): 
#        if image_tag:
#            image_url = self.get_image_url(image_tag)
#            if image_url:
#                extra_vars = {'image_url': image_url}
#        else:
#            image_url = self.get_s3_image_url()
#            extra_vars = {'image_url': image_url}
#        return self.load_general_manifest(manifest_type='deploy', extra_vars=extra_vars)

#    def load_general_manifest(self, manifest_type='configmap', image_tag=None):
#        if image_tag:
#            image_url = self.get_image_url(image_tag)
#            if image_url:
#                extra_vars = {'image_url': image_url}
#        else:
#            image_url = self.get_s3_image_url()
#            extra_vars = {'image_url': image_url}
#        return self.load_general_manifest(manifest_type=manifest_type, extra_vars=extra_vars)



    def load_general_manifest(self, manifest_type, runtime_env, aws_region, extra_vars=None):
        if manifest_type=='deploy' and not extra_vars:
            image_url = self.get_s3_image_url(runtime_env, aws_region)
            extra_vars = {'image_url': image_url}
        return super().load_general_manifest(manifest_type, runtime_env, aws_region, extra_vars=extra_vars)

