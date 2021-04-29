from flask import url_for
import pprint

test_assumption = 'test_assumption'

def test_app(client):
    print(url_for('healthcheck'))

    r = client.get(url_for('healthcheck'))
    assert r.status_code == 200

    print(r.json)

    assert r.json['status'] == 'OK'

def test_poke(client):
    r = client.get(url_for('poke'))
    assert r.status_code == 200

def test_evaluate_get(client, auth_header):
    r = client.get(url_for('evaluate', api_version="v2.0", target="echo_cmd", assume=test_assumption),                   
                   headers=auth_header
                  )

    print(r)

    assert r.status_code == 200

    print(pprint.pformat(r.json))
    assert f'-a {test_assumption}' in " ".join(r.json['result'])

def test_evaluate_post(client, auth_header):

    r = client.post(url_for('evaluate', api_version="v2.0", target="echo_cmd"),
                    data={'assume': test_assumption},
                    headers=auth_header
                  )

    print(r)

    assert r.status_code == 200

    print(pprint.pformat(r.json))
    print(r.json['result'])

    assert f'-a {test_assumption}' in " ".join(r.json['result'])
