"""Browser boundary tests: prevent malicious sites from driving localhost APIs."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.local_http_guard import check_browser_request


@pytest.mark.parametrize('host', [
    'evil.example', 'localhost.evil.example', '127.0.0.1.evil.example',
    'localhost@evil.example', '127.0.0.1:999999', '127.0.0.1\\evil.example',
    '[::1', '',
])
def test_non_local_hosts_rejected(host):
    assert check_browser_request(host_header=host, scheme='http', origin=None, fetch_site=None) is not None


@pytest.mark.parametrize('origin', [
    'https://evil.example', 'http://evil.example', 'null',
    'http://127.0.0.1.evil.example:8000', 'http://localhost:8000',
    'http://127.0.0.1:9000', 'http://127.0.0.1:8000/path',
    'http://bad:pw@127.0.0.1:8000', '',
])
def test_foreign_browser_origins_rejected(origin):
    assert check_browser_request(host_header='127.0.0.1:8000',scheme='http',
                                 origin=origin,fetch_site=None) is not None


def test_same_origin_and_native_command_line_still_work():
    assert check_browser_request(host_header='127.0.0.1:8000',scheme='http',
                                 origin='http://127.0.0.1:8000',fetch_site='same-origin') is None
    assert check_browser_request(host_header='[::1]:8000',scheme='http',origin=None,
                                 fetch_site=None) is None
    assert check_browser_request(host_header='127.0.0.1:8000',scheme='http',
                                 origin=None,fetch_site='cross-site') is not None


def test_malicious_form_blocked_before_handler(monkeypatch, tmp_path):
    monkeypatch.setenv('VIRALOS_DB', str(tmp_path/'guard.sqlite'))
    with TestClient(app) as client:
        assert client.get('/health',headers={'host':'evil.example'}).status_code==403
        body={'name':'Owner local only','sport_id':'cricket','locale':'en-US',
              'market':'India','timezone':'Asia/Kolkata'}
        assert client.post('/api/channels', json=body, headers={'origin':'https://attacker.invalid'}).status_code==403
        assert client.post('/api/channels', json=body, headers={'sec-fetch-site':'cross-site'}).status_code==403
        assert client.post('/api/channels', json=body, headers={'origin':'http://testserver'}).status_code==200
