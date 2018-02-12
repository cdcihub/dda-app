#!flask/bin/python
from __future__ import print_function

from flask import Flask, url_for, jsonify, send_file, request
import pylru

import sys
import time
import yaml
import json
import re
import os
import requests
import ddosaauth
import pilton
import socket
import subprocess
from flask import request
from flask import jsonify


import logging
import ddasentry
import ddalogzio
import ddalogstash
    
def dlog(*a,**aa):
    level=logging.INFO
    if 'level' in aa:
        level=aa.pop('level')
    ddalogstash.logger.log(level,*a,**aa)


context=socket.gethostname()

app = Flask(__name__)

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

        ddalogzio.logger.info(dict(action="requested",target=target,modules=modules,assume=assume,inject=inject,client=client,token=client,hostname=socket.gethostname(),callback=callback))
        ddalogstash.logger.info(dict(action="requested",target=target,modules=modules,assume=assume,inject=inject,client=client,token=client,hostname=socket.gethostname(),callback=callback))

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
            cmd+=["-D",os.environ["DDA_QUEUE"]]

        if callback is not None:
            print("callback:",callback)
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
                line = p.stdout.readline()
                if not line:
                    break
                print('{log:heatool}',line,end='')
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

            try:
                d=json.load(open("object_data.json"))
            except:
               # ddasentry.client.captureException()
                d="unreable"
            
            try:
                exceptions=yaml.load(open("exception.yaml"))
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
                h="unreable"

            try:
                cps=[l.split()[1] for l in open("object_url.txt")]
            except:
                #ddasentry.client.captureException()
                cps="unreable"

            if len(exceptions)==0:
                ddalogzio.logger.info(dict(action="success: returning",data=d,target=target,modules=modules,assume=assume,inject=inject,client=client,token=token,exceptions=exceptions,hostname=socket.gethostname()))
            else:
                ddasentry.client.captureMessage('Something went fundamentally wrong')
                ddalogzio.logger.warning(dict(action="warning: returning",data=d,target=target,modules=modules,assume=assume,inject=inject,client=client,token=token,exceptions=exceptions,hostname=socket.gethostname()))
            return self.all_output,d,h,cps,exceptions
        except Exception as e:
            print("exceptions:",e)
            if self.all_output=="":
                self.all_output=p.stdout.read()
                
            self.event_history.append(dict(
                event='generic failed',
                cmd=cmd,
                timestamp=timestamp()
            ))

            r=dict(status='ERROR',exception=repr(e),output=self.all_output)
            
            ddalogzio.logger.error(dict(action="exception: returning",data=r,target=target,modules=modules,assume=assume,inject=inject,client=client,token=token,hostname=socket.gethostname()))
            ddasentry.client.captureException(extra=r)
            return r,None,None,None,None

the_one_worker=Worker()

@app.route('/api/<string:api_version>/<string:target>', methods=['GET'])
@ddosaauth.requires_auth
def ddosaworker(api_version,target):
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

    prompt_delegate = False
    if api_version == "v2.0":
        prompt_delegate=True

    result,data,hashe,cached_path,exceptions=the_one_worker.run_dda(
        target,
        modules,
        assume,
        inject,
        token=token,
        prompt_delegate=prompt_delegate,
        callback=callback,
    )

    r={'modules':modules,'assume':assume,'result':result,'data':data,'hashe':hashe,'cached_path':cached_path, 'exceptions':exceptions}

    return jsonify(r)

@app.route('/poke', methods=['GET'])
def poke():
    return ""

if __name__ == '__main__':
    try:
        from export_service import export_service,pick_port
        os.environ['EXPORT_SERVICE_PORT']="%i"%pick_port("")
        port=export_service("integral-ddosa-worker","/poke",interval=0.1,timeout=0.2)
    except ImportError:
        print("consular mode failed, standalone service")
        port=int(os.environ['EXPORT_SERVICE_PORT'])

    host=os.environ['EXPORT_SERVICE_HOST'] if 'EXPORT_SERVICE_HOST' in os.environ else '127.0.0.1'
    dlog("starting integral-ddosa-worker",level=logging.INFO)

    ##
    app.run(debug=False,port=port,host=host,threaded=True)
