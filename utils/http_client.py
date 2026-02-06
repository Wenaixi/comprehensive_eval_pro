from __future__ import annotations

from typing import Any, Iterable, Optional

import logging

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    Retry = None

DEFAULT_TIMEOUT = 10


def create_session(
    *,
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Iterable[int] = (429, 500, 502, 503, 504),
    allowed_methods: Iterable[str] = ("GET", "HEAD", "OPTIONS"),
) -> requests.Session:
    session = requests.Session()

    if Retry is None or retries <= 0:
        return session

    try:
        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=backoff_factor,
            status_forcelist=tuple(status_forcelist),
            allowed_methods=frozenset(m.upper() for m in allowed_methods),
            raise_on_status=False,
        )
    except TypeError:
        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=backoff_factor,
            status_forcelist=tuple(status_forcelist),
            method_whitelist=frozenset(m.upper() for m in allowed_methods),
            raise_on_status=False,
        )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    logger: Optional[logging.Logger] = None,
    **kwargs: Any,
) -> Optional[Any]:
    log = logger or logging.getLogger(__name__)

    try:
        resp = session.request(method=method, url=url, timeout=timeout, **kwargs)
    except requests.RequestException as e:
        log.error(f"HTTP 请求失败: {method} {url} ({e})")
        return None

    try:
        data = resp.json()
    except ValueError:
        log.error(f"HTTP 响应非 JSON: {method} {url} (status={resp.status_code})")
        return None

    if resp.status_code >= 400:
        log.error(f"HTTP 响应错误: {method} {url} (status={resp.status_code})")

    return data


def request_json_response(
    session: requests.Session,
    method: str,
    url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
    logger: Optional[logging.Logger] = None,
    **kwargs: Any,
) -> tuple[Optional[Any], Optional[requests.Response]]:
    log = logger or logging.getLogger(__name__)

    try:
        resp = session.request(method=method, url=url, timeout=timeout, **kwargs)
    except requests.RequestException as e:
        log.error(f"HTTP 请求失败: {method} {url} ({e})")
        return None, None

    try:
        data = resp.json()
    except ValueError:
        log.error(f"HTTP 响应非 JSON: {method} {url} (status={resp.status_code})")
        return None, resp

    if resp.status_code >= 400:
        log.error(f"HTTP 响应错误: {method} {url} (status={resp.status_code})")

    return data, resp
