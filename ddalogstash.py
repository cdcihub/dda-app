import logging
import logstash
import sys

host = 'localhost'

logger = logging.getLogger('python-logstash-logger')
logger.setLevel(logging.DEBUG)
logger.addHandler(logstash.TCPLogstashHandler(host, 5000, version=1))

#logger.error('python-logstash: test logstash error message.')
#logger.info('python-logstash: test logstash info message.')
#logger.warning('python-logstash: test logstash warning message.')

# add extra field to logstash message
extra = {
    'python version:':repr(sys.version_info),
}
logger.addHandler(logging.StreamHandler())

logger.info('python-logstash: initializing', extra=extra)
