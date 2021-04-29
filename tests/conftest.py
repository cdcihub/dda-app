import pytest
import base64

import ddaworker.service
import ddaworker.ddaauth 

@pytest.fixture
def app():
    app = ddaworker.service.app
    return app

@pytest.fixture
def auth():
    return ddaworker.ddaauth.get_server_auth()

@pytest.fixture
def auth_header(auth):
    valid_credentials = base64.b64encode(b"{auth[0]}:{auth[1]}").decode("utf-8")
    return {"Authorization": "Basic " + valid_credentials}
