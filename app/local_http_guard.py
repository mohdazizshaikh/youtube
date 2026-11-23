"""Local UI host and browser Origin/Fetch-Metadata isolation.

ViralOS is a localhost-only operator app. A malicious website could attempt
cross-site form uploads or DNS rebinding even without a permissive CORS policy.
This guard rejects non-local Host headers and foreign browser Origins *before*
any write route is reached. Native/CLI requests without Origin still work;
this is not authentication against malware running on the owner's computer.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit
from fastapi import Request
from fastapi.responses import JSONResponse

LOOPBACK = frozenset({'localhost', '127.0.0.1', '::1'})


def _authority(host_header: str, *, default_port: int) -> tuple[str, int] | None:
    if not host_header or any(c in host_header for c in '/\\@?# \t\n\r'):
        return None
    try:
        value = urlsplit('//'+host_header)
        hostname = (value.hostname or '').lower().rstrip('.')
        port = value.port if value.port is not None else default_port
        if not 1 <= port <= 65535 or value.username or value.password or value.path:
            return None
        return hostname, port
    except ValueError:
        return None


def _test_hosts() -> frozenset[str]:
    # pytest TestClient defaults to the synthetic host 'testserver'. Never
    # permit that host in a normal owner-running uvicorn process.
    return frozenset({'testserver'}) if (os.getenv('PYTEST_CURRENT_TEST') or
                                           os.getenv('VIRALOS_INTERNAL_TEST_CLIENT') == '1') else frozenset()


def check_browser_request(*, host_header: str, scheme: str, origin: str | None,
                          fetch_site: str | None) -> str | None:
    if scheme not in ('http', 'https'):
        return 'UNSUPPORTED_LOCAL_SCHEME'
    default_port = 443 if scheme == 'https' else 80
    authority = _authority(host_header, default_port=default_port)
    if authority is None or authority[0] not in LOOPBACK | _test_hosts():
        return 'NON_LOCAL_HOST_REJECTED'
    if fetch_site in ('cross-site', 'same-site'):
        return 'CROSS_ORIGIN_BROWSER_REQUEST_REJECTED'
    if origin is not None:
        try:
            parsed = urlsplit(origin)
            if (parsed.scheme != scheme or parsed.username or parsed.password or
                    parsed.path or parsed.query or parsed.fragment or
                    _authority(parsed.netloc, default_port=default_port) != authority):
                return 'FOREIGN_ORIGIN_REJECTED'
        except ValueError:
            return 'FOREIGN_ORIGIN_REJECTED'
    return None


async def local_http_guard(request: Request, call_next):
    problem = check_browser_request(
        host_header=request.headers.get('host', ''), scheme=request.url.scheme,
        origin=request.headers.get('origin'),
        fetch_site=request.headers.get('sec-fetch-site'))
    if problem:
        return JSONResponse(status_code=403, content={'detail': problem})
    return await call_next(request)
