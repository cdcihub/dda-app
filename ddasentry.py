import os
from raven import Client

client = Client(open(os.environ['HOME']+"/.sentry-key").read().strip())

