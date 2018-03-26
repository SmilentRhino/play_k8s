import logging
import fire
import config
from micro_service import MicroService
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

def validate_manifests(aws_region,
                    runtime_env,
                    debug=True):
    set_log_level(debug)
    all_changed = [] 
    runtime_envs = config.get_runtime_envs(runtime_env)
    for env in runtime_envs:
        for region in config.get_regions(env, aws_region):
            cm = ClusterManager(runtime_env=env, aws_region=region)
            result = cm.validate()
            if not result['status']:
                for change in result['changed_list']:
                    all_changed.append(env + ' ' + region + ' ' + ' '.join(change))
    if all_changed:
        for change in all_changed:
            logging.info('%s has changed', change)
    else:
        logging.info('%s in %s are all as expected', aws_region, runtime_env)


if __name__ == '__main__':
    fire.Fire(validate_manifests)
