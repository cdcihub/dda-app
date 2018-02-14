import logging
import logging.config

logging.config.fileConfig('logzio.conf')
logger = logging.getLogger('restddosaworkerLogzioLogger')

logger.info('starting restddosaworker logzio logger')

