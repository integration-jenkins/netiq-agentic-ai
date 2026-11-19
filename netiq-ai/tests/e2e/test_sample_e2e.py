"""Sample end-to-end test (skipped until the service is runnable)."""
import pytest


@pytest.mark.skip(reason="enable once the API service can be started in tests")
def test_health_endpoint():
    ...  # GET /health -> 200
