#!flask/bin/python

from flask import Flask, url_for, jsonify, send_file, request
import pylru

import sys
import json
import re
import os
import requests
import ddosaauth
import pilton
import socket
import subprocess

try:
    from dlogging import logging
    from dlogging import log as dlog
except ImportError:
    def dlog(*a,**aa):
        print a,aa
    import logging


context=socket.gethostname()

app = Flask(__name__)


def run_dda(target,modules,assume):
    cmd=["rundda.py",target,"-j","-c"] # it's peculiar but it is a level of isolation

    dlog(logging.INFO,"starting "+repr(cmd))
    
    for module in modules:
        cmd+=["-m",module]

    if assume!="":
        cmd+=["-a",assume]

    print "$ "+" ".join(cmd)
    p=subprocess.Popen(cmd,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)
    try:
        all_output=""
        while True:
            line = p.stdout.readline()
            if not line:
                break
            print '{log:heatool}',line,
            all_output+=line

        p.wait()

        try:
            d=json.load(open("object_data.json"))
        except:
            d="unreable"

        try:
            h=open("reduced_hashe.txt").read()
        except:
            h="unreable"

        try:
            cps=[l.split()[1] for l in open("object_url.txt")]
        except:
            cps="unreable"

        return all_output,d,h,cps
    except Exception as e:
        r=('ERROR',repr(e),str(e),p.stdout.read())
        return r,None,None,None

@app.route('/api/v1.0/<string:target>', methods=['GET'])
@ddosaauth.requires_auth
def ddosaworker(target):

    modules=[]
    if 'modules' in request.args:
        modules+=request.args['modules'].split(",")

    assume=""
    if 'assume' in request.args:
        assume=request.args['assume']


    result,data,hashe,cached_path=run_dda(target,modules,assume)

    r={'modules':modules,'assume':assume,'result':result,'data':data,'hashe':hashe,'cached_path':cached_path}

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
    dlog(logging.INFO,"starting integral-ddosa-worker")

    ##
    app.run(debug=False,port=port,host=host)
