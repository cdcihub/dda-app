import pytest
import json
import random
import time
import io

from flask import url_for
import pprint

test_assumption = 'test_assumption'
test_modules = 'test_modules'

def test_app(client):
    print(url_for('healthcheck'))

    r = client.get(url_for('healthcheck'))
    assert r.status_code == 200

    print(r.json)

    assert r.json['status'] == 'OK'

def test_poke(client):
    r = client.get(url_for('poke'))
    assert r.status_code == 200

@pytest.mark.parametrize('method', ['get', 'post', 'post-data', 'post-json'])
def test_evaluate(client, auth_header, method):

    if method == 'post-json':
        r = client.post(url_for('evaluate', api_version="v2.0", target="echo_cmd", ),
                    data=json.dumps(dict(assume=test_assumption, modules=test_modules)),
                    headers=auth_header
                    )
    elif method == 'post-data':
        r = client.post(url_for('evaluate', api_version="v2.0", target="echo_cmd", ),
                    data=json.dumps(dict(assume=test_assumption, modules=test_modules)),
                    headers=auth_header
                    )
    elif method in [ 'post', 'get' ]:
        r = getattr(client, method)(url_for('evaluate', api_version="v2.0", target="echo_cmd", assume=test_assumption, modules=test_modules),
                    headers=auth_header
                    )

    print(r)

    assert r.status_code == 200

    print(pprint.pformat(r.json))
    print(r.json['result'])

    assert f'-a {test_assumption}' in " ".join(r.json['result'])
    assert f'-m {test_modules}' in " ".join(r.json['result'])



#@pytest.mark.parametrize('return_file_contents', [True, False])
def test_dda_module(client, auth_header):

    random_version = "{}.{}".format(
        time.strftime("%Y%m%d.%H%M%S%s"),
        random.random()
    )

    r = client.post(url_for('evaluate', api_version="v2.0", target="DDATest", ),
                data=json.dumps(dict(
                    assume=f"ddatest.DDATest(use_version='{random_version}')", 
                    modules="ddatest",
                    )),
                headers=auth_header
                )        

    print(r)

    assert r.status_code == 200

    data = r.json

    print(data)

    for k, v in data['data'].items():

        if isinstance(v, list) and len(v) > 0 and v[0] == "DataFile":
            print("found file:", k, v)                
            
            r = client.get(url_for('fetch_ddcache_file', api_version="v2.0", target="DDATest", 
                        cached_path=data['cached_path'],
                        filename=v[1]
                        ),
                    headers=auth_header
                    )

            print(r, r.data)
            
            fn = "returned_data_file.json"

            open(fn, "wb").write(r.data)
            
#            print(json.load(open(fn)))


 