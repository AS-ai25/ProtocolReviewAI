"""Security of the API (19 November 2026): the secret, the download guard, the PDF limits and the rate limits.

Code only; nothing here calls a model. Every limit is a setting (config.py) and 0 switches it off.

* **Secret.** Compared in constant time. An empty or default secret (`change-me`) is accepted only from this machine, so
  a local demonstration works out of the box and a server on the network never runs unprotected: a client on the
  network gets 503, and `serve` refuses to start on a network address (`startup_problem`). A request forwarded by a
  proxy on this machine (ngrok, nginx) counts as a client on the network (`client_address`). Wrong secrets are counted
  per client address; after `auth_failures_per_5min` the address gets 429 for the rest of the window.
* **Download guard** (`/webhook/protocol-url`). Only http/https, no credentials in the URL, and every address the host
  resolves to must be public: loopback, private, link-local (cloud metadata), carrier-grade NAT, multicast and reserved
  ranges are refused. Redirects are followed by hand, at most `download_max_redirects`, and every hop is checked the same
  way. The body is read as a stream and cut at the size limit. Not covered: a host whose DNS answer changes between the
  check and the connection (DNS rebinding); `download_allowed_hosts` closes that when the sources are known.
* **PDF limits.** Size, page count, extracted characters and reading time, checked before a run is created, so a
  document that would exhaust the server or the model budget is refused with a clear message. Password-protected and
  unreadable files are refused as well.
* **Rate limits.** Reviews started per client address per minute and by all clients per hour (every review costs model
  calls). In memory, one process. Behind a proxy on another machine the client address is the proxy's.
"""
from __future__ import annotations

import hmac
import ipaddress
import logging
import socket
import threading
import time
from collections import deque
from urllib.parse import urljoin, urlsplit

import httpx
import pymupdf
from fastapi import HTTPException

from .config import settings

log = logging.getLogger(__name__)

WEAK_SECRETS = {"", "change-me", "changeme", "secret", "password", "admin", "test"}
REDIRECTS = {301, 302, 303, 307, 308}


# ------------------------------------------------------------------- limiter
class SlidingWindow:
    """Events per key inside a moving time window. Thread-safe, in memory."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _live(self, key: str, window_s: float, now: float) -> deque[float]:
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] >= window_s:
            q.popleft()
        return q

    def count(self, key: str, window_s: float, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._live(key, window_s, now)
            if not q:
                self._hits.pop(key, None)
            return len(q)

    def add(self, key: str, now: float | None = None) -> None:
        with self._lock:
            self._hits.setdefault(key, deque()).append(time.monotonic() if now is None else now)

    def allow(self, key: str, limit: int, window_s: float, now: float | None = None) -> tuple[bool, int]:
        """Records the event when it is inside the limit. Returns (allowed, seconds until the next one is allowed)."""
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._live(key, window_s, now)
            if len(q) >= limit:
                return False, max(1, int(window_s - (now - q[0])) + 1)
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_failures = SlidingWindow()
review_starts = SlidingWindow()


# -------------------------------------------------------------------- secret
def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def client_address(peer: str, forwarded_for: str = "") -> str:
    """The address a request is attributed to. A request that a proxy on this machine forwarded (ngrok, nginx: the peer
    is loopback and `X-Forwarded-For` is set) comes from the network, so it is attributed to the address the proxy
    recorded and never counts as local. From any other peer the header is ignored: a client can write anything in it."""
    forwarded = [a.strip() for a in (forwarded_for or "").split(",") if a.strip()]
    if forwarded and is_loopback(peer):
        return forwarded[-1] if not is_loopback(forwarded[-1]) else "forwarded"
    return peer


def secret_is_weak(secret: str | None = None) -> bool:
    return (settings.webhook_secret if secret is None else secret).strip().lower() in WEAK_SECRETS


def startup_problem(host: str) -> str | None:
    """Why the server must not start on `host` with the current secret, or None."""
    if secret_is_weak() and (settings.require_strong_secret or not is_loopback(host)):
        return ("WEBHOOK_SECRET is empty or a default value. Set a secret of your own in .env before starting the server"
                + ("." if settings.require_strong_secret else f" on a network address ({host})."))
    return None


def check_secret(given: str, client_host: str) -> None:
    expected = settings.webhook_secret
    if secret_is_weak(expected) and (settings.require_strong_secret or not is_loopback(client_host)):
        raise HTTPException(status_code=503, detail="the server has no secret of its own (WEBHOOK_SECRET is empty or a default "
                                                    "value); set one in .env and restart the server")
    window, limit = 300.0, settings.auth_failures_per_5min
    if limit and auth_failures.count(client_host, window) >= limit:
        raise HTTPException(status_code=429, detail="too many requests with a wrong X-Webhook-Secret; try again later",
                            headers={"Retry-After": "300"})
    if expected and not hmac.compare_digest((given or "").encode("utf-8"), expected.encode("utf-8")):
        auth_failures.add(client_host)
        raise HTTPException(status_code=401, detail="invalid X-Webhook-Secret")


def check_rate(client_host: str) -> None:
    """Called after the secret check, on the endpoints that start a review."""
    for key, limit, window, what in ((f"ip:{client_host}", settings.rate_limit_per_minute, 60.0, "from this address per minute"),
                                     ("all", settings.rate_limit_per_hour, 3600.0, "per hour")):
        if not limit:
            continue
        ok, retry = review_starts.allow(key, limit, window)
        if not ok:
            log.warning("rate limit: %s reviews %s reached (client %s)", limit, what, client_host)
            raise HTTPException(status_code=429, detail=f"rate limit: at most {limit} reviews {what}; retry in {retry} s",
                                headers={"Retry-After": str(retry)})


# ------------------------------------------------------------ download guard
def _resolve(host: str) -> list[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})


def _public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def validate_download_url(url: str, resolve=_resolve) -> None:
    """Raises 400 unless `url` is an http(s) address of a public host (and of an allowed host, when a list is set)."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower().rstrip(".")
    if parts.scheme not in ("http", "https") or not host:
        raise HTTPException(status_code=400, detail="file_url must be an http or https address")
    if parts.username or parts.password:
        raise HTTPException(status_code=400, detail="file_url must not contain credentials")
    allowed = [a.lower().lstrip(".") for a in settings.download_allowed_hosts]
    if allowed and not any(host == a or host.endswith("." + a) for a in allowed):
        raise HTTPException(status_code=400, detail="file_url host is not in DOWNLOAD_ALLOWED_HOSTS")
    try:
        addresses = resolve(host)
    except OSError:
        raise HTTPException(status_code=400, detail="file_url host could not be resolved") from None
    if not addresses or not all(_public(a) for a in addresses):
        log.warning("download refused: %s resolves to a non-public address", host)
        raise HTTPException(status_code=400, detail="file_url must point to a public internet host")


async def fetch_pdf(url: str, *, resolve=_resolve, transport: httpx.AsyncBaseTransport | None = None) -> bytes:
    """Download with every hop validated and the body cut at the size limit."""
    limit = settings.max_pdf_mb * 1024 * 1024
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False, transport=transport) as client:
            for _ in range(settings.download_max_redirects + 1):
                validate_download_url(url, resolve)
                async with client.stream("GET", url) as r:
                    if r.status_code in REDIRECTS and r.headers.get("location"):
                        url = urljoin(url, r.headers["location"])
                        continue
                    r.raise_for_status()
                    body = bytearray()
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > limit:
                            raise HTTPException(status_code=413, detail=f"PDF larger than {settings.max_pdf_mb} MB")
                    return bytes(body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"could not download file ({type(exc).__name__})") from None
    raise HTTPException(status_code=400, detail="could not download file (too many redirects)")


# ---------------------------------------------------------------- PDF limits
def inspect_pdf(data: bytes) -> dict:
    """Refuses a file that is not a readable PDF inside the limits. Returns {pages, chars}."""
    if not data[:5].startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="file is not a PDF")
    if len(data) > settings.max_pdf_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PDF larger than {settings.max_pdf_mb} MB")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:  # noqa: BLE001 - any parser error means the file is not a usable PDF
        raise HTTPException(status_code=400, detail="file could not be opened as a PDF") from None
    with doc:
        if doc.needs_pass:
            raise HTTPException(status_code=400, detail="PDF is password-protected")
        pages = doc.page_count
        if pages == 0:
            raise HTTPException(status_code=400, detail="PDF has no pages")
        if settings.max_pdf_pages and pages > settings.max_pdf_pages:
            raise HTTPException(status_code=413, detail=f"PDF has {pages} pages; the limit is {settings.max_pdf_pages}")
        started, chars = time.monotonic(), 0
        try:
            for page in doc:
                chars += len(page.get_text("text"))
                if settings.max_protocol_chars and chars > settings.max_protocol_chars:
                    raise HTTPException(status_code=413, detail=f"PDF text is longer than {settings.max_protocol_chars:,} characters")
                if settings.pdf_inspect_timeout_s and time.monotonic() - started > settings.pdf_inspect_timeout_s:
                    raise HTTPException(status_code=413, detail=f"PDF takes longer than {settings.pdf_inspect_timeout_s} s to read")
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001
            raise HTTPException(status_code=400, detail="PDF pages could not be read") from None
    return {"pages": pages, "chars": chars}
