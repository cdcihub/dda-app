#!flask/bin/python

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

try:
    from dlogging import logging
    from dlogging import log as dlog
except ImportError:
    def dlog(*a,**aa):
        print a,aa
    import logging


context=socket.gethostname()

app = Flask(__name__)

def timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

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

    def run_dda(self,target,modules,assume,inject,client=None,token=None):
        client=request.remote_addr

        if self.task is not None:
            r=dict(status='busy',task=self.task,output=self.all_output)
            return r,None,None,None
        
        if target == "poke":
            return self.all_output,self.format_status(),"",""
        
        if target == "history":
            status=self.format_status()
            status['history']=self.event_history
            return self.all_output,status,"",""
        
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
            return '\nwell slept!\n\n'+self.all_output,{},"",""


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


        print "$ "+" ".join(cmd)
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
                print '{log:heatool}',line,
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
                d="unreable"
            
            try:
                exceptions=yaml.load(open("exception.yaml"))
            except Exception as e:
                exceptions="unreable"
                if rundda_exception is not None:
                    print("unable to read exception while rundda failed",e)
                    raise rundda_exception

            try:
                h=open("reduced_hashe.txt").read()
            except:
                h="unreable"

            try:
                cps=[l.split()[1] for l in open("object_url.txt")]
            except:
                cps="unreable"

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
            return r,None,None,None,None

the_one_worker=Worker()

@app.route('/api/v1.0/<string:target>', methods=['GET'])
@ddosaauth.requires_auth
def ddosaworker(target):
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

    result,data,hashe,cached_path,exceptions=the_one_worker.run_dda(target,modules,assume,inject,token=token)

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
        print "consular mode failed, standalone service"
        port=int(os.environ['EXPORT_SERVICE_PORT'])

    host=os.environ['EXPORT_SERVICE_HOST'] if 'EXPORT_SERVICE_HOST' in os.environ else '127.0.0.1'
    dlog("starting integral-ddosa-worker",level=logging.INFO)

    ##
    app.run(debug=False,port=port,host=host,threaded=True)
