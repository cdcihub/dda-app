import logging
import logging.config

# Say i have saved my configuration under ./myconf.conf
logging.config.fileConfig('logzio.conf')
logger = logging.getLogger('restddosaworkerLogzioLogger')

logger.info('starting restddosaworker logger')

