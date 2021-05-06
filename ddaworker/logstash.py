import sys
import os

import logging
from logstash_formatter import LogstashFormatterV1

logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
formatter = LogstashFormatterV1()

handler.setFormatter(formatter)
logger.addHandler(handler)

extra = {
    'python version:':repr(sys.version_info),
}

logger.info('python-logstash: initializing %s', extra)
