from flask import url_for
import pprint

def test_app(client):
    print(url_for('healthcheck'))

    assert client.get(url_for('healthcheck')).status_code == 200

def test_root(client):
    assert client.get(url_for('poke')).status_code == 200

def test_evaluate(client):
    r = client.get(url_for('evaluate', api_version="v2.0", target="test"))
    assert r.status_code == 200

    print(pprint.pformat(r.json))

    print(r.json['result'])
