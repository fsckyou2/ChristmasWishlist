"""Outbound HTTP for the product scraper, guarded against SSRF.

Users give us URLs to fetch, and the app runs on a home server, so a naive fetch can reach the LAN (the NAS admin
API, routers, other apps). This module:

* only allows http/https on ports 80 and 443,
* resolves the hostname and refuses non-public addresses up front (for a clear error message),
* re-checks the address the socket actually connected to, on every connection, which also covers redirects and
  DNS rebinding,
* follows at most a few redirects, re-validating each hop,
* ignores proxy environment variables, and caps the (decompressed) response size.
"""

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool

ALLOWED_PORTS = {80, 443}
MAX_REDIRECTS = 5


class BlockedDestination(ValueError):
    """The URL points somewhere we refuse to fetch. (Not an OSError, so urllib3 won't retry or wrap it.)"""


class ResponseTooLarge(ValueError):
    pass


def is_public_ip(value):
    addr = ipaddress.ip_address(value)
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def check_url(url):
    """Raise BlockedDestination unless `url` is http(s), on an allowed port, and resolves only to public IPs."""
    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https") or not parts.hostname:
        raise BlockedDestination("Only http:// and https:// URLs can be fetched.")
    try:
        port = parts.port or (443 if scheme == "https" else 80)
    except ValueError:
        raise BlockedDestination("Invalid port.")
    if port not in ALLOWED_PORTS:
        raise BlockedDestination("Only standard web ports (80/443) can be fetched.")
    try:
        infos = socket.getaddrinfo(parts.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise BlockedDestination("That website's address could not be found.")
    if not infos or not all(is_public_ip(info[4][0]) for info in infos):
        raise BlockedDestination("That address is not on the public internet.")


class _PublicPeerOnly:
    def _new_conn(self):
        sock = super()._new_conn()
        try:
            peer = sock.getpeername()[0]
        except OSError:
            sock.close()
            raise
        if not is_public_ip(peer):
            sock.close()
            raise BlockedDestination("That address is not on the public internet.")
        return sock


class _GuardedHTTPConnection(_PublicPeerOnly, HTTPConnection):
    pass


class _GuardedHTTPSConnection(_PublicPeerOnly, HTTPSConnection):
    pass


class _GuardedHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = _GuardedHTTPConnection


class _GuardedHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = _GuardedHTTPSConnection


class _GuardedAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme = {
            "http": _GuardedHTTPConnectionPool,
            "https": _GuardedHTTPSConnectionPool,
        }


def _session():
    session = requests.Session()
    session.trust_env = False  # never route through HTTP(S)_PROXY from the environment
    adapter = _GuardedAdapter(max_retries=0)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_text(url, *, headers=None, params=None, timeout=10, max_bytes=3 * 1024 * 1024):
    """GET `url` safely and return the decoded body. Raises BlockedDestination, ResponseTooLarge, or
    requests.RequestException (including HTTPError for 4xx/5xx)."""
    with _session() as session:
        for _ in range(MAX_REDIRECTS + 1):
            check_url(url)
            response = session.get(
                url, headers=headers, params=params, timeout=timeout, stream=True, allow_redirects=False
            )
            with response:
                if response.is_redirect:
                    url = urljoin(response.url, response.headers.get("Location", ""))
                    params = None  # already part of response.url
                    continue
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise ResponseTooLarge("That page is too large to read.")
                return bytes(body).decode(response.encoding or "utf-8", errors="replace")
        raise requests.TooManyRedirects("Too many redirects.")
