import pytest

import ddaworker.service

@pytest.fixture
def app():
    app = ddaworker.service.app
    return app
