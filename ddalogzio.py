import os
import logging
import logging.config


if os.environ.get('RESTDDOSAWORKER_LOGZIO_ENABLE','no')=='yes':
    logging.config.fileConfig('logzio.conf')
    logger = logging.getLogger('restddosaworkerLogzioLogger')
    logger.info('starting restddosaworker logzio logger')
else:
    logger=logging.getLogger("logz")
    logger.info('starting restddosaworker logzio logger')

logger=logging.getLogger("logz")
