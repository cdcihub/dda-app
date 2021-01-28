#!flask/bin/python

import json
import socket
import subprocess
import random
import time
import re
import glob

import yaml
import urllib.parse
from flask import Flask
from flask import request
from flask import jsonify

from . import ddosaauth

import logging
from . import ddasentry
#import ddalogzio
from . import ddalogstash
import mattersend

import dataanalysis.core

logger = logging.getLogger(__name__)

def dlog(*a,**aa):
    level=logging.INFO
    if 'level' in aa:
        level=aa.pop('level')
    message="; ".join(a)
    ddalogstash.logger.log(level,message,extra=aa)


context=socket.gethostname()

def create_app():
    return Flask(__name__)

app = create_app()

class JSON_Improved(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, dataanalysis.core.AnalysisDelegatedException):
            return json.dumps(obj.__dict__)
        else:
            return super().default(obj)

def timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

import os, errno

def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e: # this would be "except OSError, e:" before Python 2.6
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occurred

class Worker(object):
    task=None
    all_output=None

    event_history=[]

    def __init__(self):
        self.alive_since=timestamp()

    def format_status(self):
        return dict(
                task=self.task,
                alive_since=self.alive_since,
            )

    def run_dda(self,target,modules,assume,inject,client=None,token=None,
                prompt_delegate=False,callback=None):

        cwd = os.getcwd()
        nwd = os.path.join(cwd,
                           target,
                           time.strftime("%Y-%m"), 
                           time.strftime("%d"), 
                           time.strftime("%H-%M-%S") + f"-{os.getpid():d}-{random.getrandbits(32):08x}")
        try:
            os.makedirs(nwd)
        except FileExistsError:
            logger.warning("trying to create one time directory '%s', but already exists? suspicious", nwd)

        try:
            os.chdir(nwd)
            R = self._run_dda(target,modules,assume,inject,client=client,token=token,
                    prompt_delegate=prompt_delegate,callback=callback)
            os.chdir(cwd)
            return R
        except Exception as e:
            os.chdir(cwd)
            raise

    def _run_dda(self,target,modules,assume,inject,client=None,token=None,
                prompt_delegate=False,callback=None):
        client=request.remote_addr

        if self.task is not None:
            r=dict(status='busy',task=self.task,output=self.all_output)
            return r,None,None,None,None
        
        if target == "poke":
            return self.all_output,self.format_status(),"","",""
        
        if target == "history":
            status=self.format_status()
            status['history']=self.event_history
            return self.all_output,status,"","",""
        
        self.event_history.append(dict(
            event='requested',
            target=target,
            modules=modules,
            assume=assume,
            client=client,
            timestamp=timestamp()
        ))

        if target.startswith("sleep"):
            self.task="sleeping"
            self.all_output=""
            for i in range(int(target.split(":")[1])):
                self.all_output+="%i\n"%i
                time.sleep(1)
            self.task=None
            return '\nwell slept!\n\n'+self.all_output,{},"","",""

        silentremove("object_data.json")
        silentremove("exception.yaml")
        silentremove("reduced_hashe.txt")
        silentremove("object_url.txt")

        #ddalogzio.logger.info(dict(action="requested",target=target,modules=modules,assume=assume,inject=inject,client=client,token=client,hostname=socket.gethostname(),callback=callback))
        dlog("requested",action="requested",target=target,modules=modules,assume=assume,inject=inject,client=client,token=client,hostname=socket.gethostname(),callback=callback)

        #TODO: try datalake here

        try:
            url_params=urllib.parse.parse_qs(urllib.parse.urlparse(callback).query)
        except:
            url_params={'session_id':'?','job_id':'?'}

        try:
            mattersend.send(
                                channel="request-log",
                                message=
                                    "|...|...|\n"+
                                    "|------------: |:---------------|\n"+
                                    "|sessionid|"+repr(url_params['session_id'])+"|\n"+
                                    "|jobid|"+repr(url_params['job_id'])+"|\n"+
                                    "|requested|"+repr(client)+"|\n"+
                                    "|target|"+repr(target)+"|\n"+
                                    "|modules|"+repr(modules)+"|\n"+
                                    "|assume|"+re.sub(" +"," ",repr(assume))+"|\n"+
                                    "|inject|"+repr(inject)+"|\n"
                                ,
                                url=open(os.environ.get("HOME")+"/.mattermost-request-log-hook").read().strip(),
                                #syntax="markdown",
                            )
        except Exception as e:
            dlog("mattermost problem",action="requested",exception=repr(e))
            #ddasentry.client.captureException()

        cmd=["rundda.py",target,"-j","-c"] # it's peculiar but it is a level of isolation

        dlog("starting "+repr(cmd),level=logging.INFO)
        
        for module in modules:
            cmd+=["-m",module]

        if assume!="":
            cmd+=["-a",assume]

        for inj in inject:
            inj_fn=inj[0]+"_data_injection.json"
            print("will inject",inj_fn)
            print(" ...",inj)
            json.dump(inj,open(inj_fn,"w"))
            cmd+=["-i",inj_fn]

        if prompt_delegate:
            cmd+=["-D",os.environ["ODAHUB"]]

        if callback is not None:
            print("callback:",callback)
            dlog("setting callback",callback=callback)
            cmd+=["--callback",callback]

        print("$ "+" ".join(cmd))
        p=subprocess.Popen(cmd,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)

        self.all_output=""
        try:
            self.task=cmd

            self.event_history.append(dict(
                event='started',
                cmd=cmd,
                timestamp=timestamp()
            ))

            while True:
                line = p.stdout.readline().decode()
                if not line:
                    break
                print(line,end='')
                #print('{log:heatool}',line,end='')
                self.all_output+=line

            p.wait()
            self.task=None
            
            self.event_history.append(dict(
                event='finished',
                cmd=cmd,
                timestamp=timestamp()
            ))

            rundda_exception=None
            if p.returncode!=0:
                self.event_history.append(dict(
                    event='rundda failed',
                    cmd=cmd,
                    timestamp=timestamp()
                ))
                rundda_exception=Exception("rundda.py failed with code %i"%p.returncode)
                print("\033[31mrunning workflow failed\033[0m")
                dlog("rundda returned",return_code=p.returncode,output=self.all_output)

            try:
                d=json.load(open("object_data.json"))
            except:
               # ddasentry.client.captureException()
                d="unreadable-object-data"
            
            try:
                exceptions=yaml.load(open("exception.yaml"), Loader=yaml.Loader)
                dlog("rundda exception",exceptions=exceptions)
            except Exception as e:
                if rundda_exception is not None:
                    print("unable to read exception while rundda failed",e)
                    raise rundda_exception
                else:
                    exceptions=[]
                    print("no exceptions")

            try:
                h=open("reduced_hashe.txt").read()
            except:
                #ddasentry.client.captureException()
                print("\033[31mERROR reading reduced_hashe.txt\033[0m, have", glob.glob("*"))
                h="unreable"

            try:
                cps=[l.split()[1] for l in open("object_url.txt")]
                print("\033[32mSUCCESS reading object_url.txt\033[0m, have", cps)
            except:
                #ddasentry.client.captureException()
                print("\033[31mERROR reading object_url.txt\033[0m, have", glob.glob("*"))
                cps="unreable"

            if len(exceptions)==0:
                report=dict(action="success: returning",data=d,target=target,modules=modules,assume=assume,inject=inject,client=client,token=token,exceptions=exceptions,hostname=socket.gethostname())
                #ddalogzio.logger.info(report)
                dlog(report['action'],**report)
            else:
                #ddasentry.client.captureMessage('Something went fundamentally wrong')
                report=dict(action="warning: returning",data=d,target=target,modules=modules,assume=assume,inject=inject,client=client,token=token,exceptions=exceptions,hostname=socket.gethostname())
                #ddalogzio.logger.warning(report)
                dlog(report['action'],**report)
            return self.all_output,d,h,cps,exceptions
        except Exception as e:
            print("exceptions:",e)
            print(traceback.format_exc())
            if self.all_output=="":
                self.all_output=p.stdout.read()
                
            self.event_history.append(dict(
                event='generic failed',
                cmd=cmd,
                timestamp=timestamp()
            ))

            r=dict(status='ERROR',exception=repr(e),output=self.all_output.decode())
            
            report=dict(action="exception: returning",data=r,target=target,modules=modules,assume=assume,inject=inject,client=client,token=token,hostname=socket.gethostname())
            #ddalogzio.logger.error(report)
            #ddasentry.client.captureException(extra=r)
            dlog(report['action'],**report)
            return r,None,None,None,None

the_one_worker=Worker()

@app.route('/api/<string:api_version>/<string:target>', methods=['GET'])
@ddosaauth.requires_auth
def evaluate(api_version,target):
    print("args",request.args)

    modules=[]
    if 'modules' in request.args:
        modules+=request.args['modules'].split(",")

    assume=""
    if 'assume' in request.args:
        assume=request.args['assume']

    inject=[]
    if 'inject' in request.args:
        inject=json.loads(request.args['inject'])

    token=None
    if 'token' in request.args:
        token=request.args['token']

    callback = None
    if 'callback' in request.args:
        callback = request.args['callback']

    #if api_version == "v2.0":
    prompt_delegate=True


    result, data, hashe, cached_path, exceptions = the_one_worker.run_dda(
        target,
        modules,
        assume,
        inject,
        token=token,
        prompt_delegate=prompt_delegate,
        callback=callback,
    )

    r = {
            'modules': modules,
            'assume': assume,
            'result': result,
            'data': data,
            'hashe': hashe,
            'cached_path': cached_path,
            'exceptions': exceptions,
        }

    J = json.loads(json.dumps(r, cls=JSON_Improved)) # make jsonifiable

    print("\033[34m", json.dumps(J, indent=4), "\033[0m")

    return J 


@app.route('/', methods=['GET'])
@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    return jsonify(dict(
            status="OK",
            container_commit = os.environ.get("CONTAINER_COMMIT","unknown"),
            osa_version = dict(
                    bundle_build = os.environ.get("OSA_VERSION", "unknown"),
                    components = open("/osa/VERSION").read() if os.path.exists("/osa/VERSION") else "unknown",
            ),
        ))



@app.route('/poke', methods=['GET'])
def poke():
    return ""

@app.route('/version', methods=['GET'])
def version():
    return jsonify(dict(
            container_commit = os.environ.get("CONTAINER_COMMIT","unknown"),
            osa_version = dict(
                    bundle_build = os.environ.get("OSA_VERSION", "unknown"),
                    components = open("/osa/VERSION").read() if os.path.exists("/osa/VERSION") else "unknown",
            ),
        ))

import traceback

@app.errorhandler(Exception)
def handle_any(e):
    logger.warning(traceback.format_exc())
    return 'bad request!', 400

if __name__ == '__main__':
    try:
        from export_service import export_service,pick_port
        port=export_service("integral-ddosa-worker","/poke",interval=0.1,timeout=0.2)
    except ImportError:
        print("consular mode failed, standalone service")
        port=8000

    host=os.environ['EXPORT_SERVICE_HOST'] if 'EXPORT_SERVICE_HOST' in os.environ else '127.0.0.1'
    dlog("starting integral-ddosa-worker",level=logging.INFO,service_host=host,service_port=port)

    ##
    app.run(debug=False,port=port,host=host,threaded=True)
