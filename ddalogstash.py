import sys
import os

import logging
from logstash_formatter import LogstashFormatterV1

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = LogstashFormatterV1()

handler.setFormatter(formatter)
logger.addHandler(handler)

#host = os.environ.get('LOGSTASH_HOST','dockerelk_logstash_1')

#logger = logging.getLogger('python-logstash-logger')
#logger.setLevel(logging.DEBUG)
#logger.addHandler(logstash.TCPLogstashHandler(host, 5000, version=1))
#logger.addHandler(logging.StreamHandler())

#logger.error('python-logstash: test logstash error message.')
#logger.info('python-logstash: test logstash info message.')
#logger.warning('python-logstash: test logstash warning message.')

# add extra field to logstash message
extra = {
    'python version:':repr(sys.version_info),
}

logger.info('python-logstash: initializing',extra)
