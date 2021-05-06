import re
import os
import mattersend

from .ddalog import dlog

def mattermost_send(url_params, 
                    client, 
                    target, 
                    modules,
                    assume,
                    inject
                    ):
    try:
        mattersend.send(
            channel="request-log",
            message="|...|...|\n" +
            "|------------: |:---------------|\n" +
            "|sessionid|"+repr(url_params['session_id'])+"|\n" +
            "|jobid|"+repr(url_params['job_id'])+"|\n" +
            "|requested|"+repr(client)+"|\n" +
            "|target|"+repr(target)+"|\n" +
            "|modules|"+repr(modules)+"|\n" +
            "|assume|"+re.sub(" +", " ", repr(assume))+"|\n" +
            "|inject|"+repr(inject)+"|\n",
            url=open(os.environ.get("HOME") +
                        "/.mattermost-request-log-hook").read().strip(),
            # syntax="markdown",
        )
    except Exception as e:
        dlog("mattermost problem", action="requested", exception=repr(e))
        # ddasentry.client.captureException()