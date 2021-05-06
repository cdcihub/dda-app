from . import logstash
import logging

def dlog(*a, **aa):
    level = logging.INFO
    if 'level' in aa:
        level = aa.pop('level')
    message = "; ".join(a)
    logstash.logger.log(level, message, extra=aa)

