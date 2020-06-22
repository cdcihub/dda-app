import os

import logging

logger = logging.getLogger()

from raven import Client

try:
    client = Client(open(os.environ['HOME']+"/.sentry-key").read().strip())
except Exception as e:
    logger.warning("unable to setup sentry")
    client = None

