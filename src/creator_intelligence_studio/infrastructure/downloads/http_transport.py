"""Transporte HTTP/HTTPS en streaming para descargas de componentes."""

from __future__ import annotations

import http.client
import ssl
from dataclasses import dataclass
from typing import Callable, Protocol
from urllib.parse import urljoin, urlsplit


class HTTPTransportError(RuntimeError):
    """Error de transporte HTTP."""


@dataclass
class HTTPTransportResponse:
    """Respuesta HTTP con lectura incremental."""

    status_code: int
    headers: dict[str, str]
    url: str
    body: object

    def read(self, size: int = -1) -> bytes:
        return self.body.read(size)  # type: ignore[attr-defined]

    def close(self) -> None:
        try:
            self.body.close()  # type: ignore[attr-defined]
        except Exception:
            pass


class ComponentHTTPTransport(Protocol):
    """Contrato para transporte HTTP/HTTPS."""

    def open(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> HTTPTransportResponse:
        raise NotImplementedError


def _response_headers(response) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in response.getheaders()}


class UrllibComponentHTTPTransport:
    """Implementacion de transporte sin dependencias extra."""

    def __init__(self, *, ssl_context: ssl.SSLContext | None = None) -> None:
        self.ssl_context = ssl_context or ssl.create_default_context()

    def _connection(self, parts):
        if parts.scheme == "https":
            return http.client.HTTPSConnection(parts.hostname, parts.port or 443, context=self.ssl_context)
        return http.client.HTTPConnection(parts.hostname, parts.port or 80)

    def open(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
    ) -> HTTPTransportResponse:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"}:
            raise HTTPTransportError(f"Esquema no soportado: {parts.scheme or 'vacío'}")
        path = parts.path or "/"
        if parts.query:
            path = f"{path}?{parts.query}"
        connection = self._connection(parts)
        connection.timeout = timeout_seconds
        try:
            connection.request(method.upper(), path, headers=headers or {})
            response = connection.getresponse()
            return HTTPTransportResponse(
                status_code=response.status,
                headers=_response_headers(response),
                url=url,
                body=response,
            )
        except Exception as exc:  # pragma: no cover - bubble up with context
            try:
                connection.close()
            except Exception:
                pass
            raise HTTPTransportError(str(exc)) from exc


def join_redirect_url(base_url: str, location: str) -> str:
    return urljoin(base_url, location)
