import logging.config

import os

def get_config():
    tried=[]
    for config in [os.environ.get('LOGZIO_CONFIG', 'logzio.conf'),os.environ['HOME']+"/.logzio.conf"]:
        if os.path.exists(config):
            return config
        tried.append(config)
    raise RuntimeError("unable to find logzio config, tried"+(", ".join(tried)))

logging.config.fileConfig(get_config())
logger = logging.getLogger('restddosaworkerLogzioLogger')

logger.info('starting restddosaworker logger')

