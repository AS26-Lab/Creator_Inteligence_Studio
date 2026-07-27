"""Protocolos de infraestructura para TikTok."""

from __future__ import annotations

from typing import Protocol


class TikTokAuthProviderClient(Protocol):
    def begin_authorization(
        self,
        *,
        client_id: str,
        scopes: tuple[str, ...],
        redirect_uri: str | None = None,
        state: str | None = None,
        code_verifier: str | None = None,
    ): ...

    def exchange_code(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        code: str,
        redirect_uri: str,
        code_verifier: str | None = None,
    ): ...

    def refresh_token(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        refresh_token: str,
    ): ...

    def revoke(self, *, client_id: str, client_secret: str | None, token: str) -> bool: ...

    def parse_redirect_response(self, query: dict[str, str]) -> dict[str, str | None]: ...


class TikTokDisplayApiClient(Protocol):
    api_version: str

    def get_user_info(self, *, token: str, fields: tuple[str, ...]) -> dict[str, object]: ...

    def list_videos(self, *, token: str, cursor: int | None = None, max_count: int | None = None, fields: tuple[str, ...]) -> dict[str, object]: ...

    def query_videos(self, *, token: str, video_ids: tuple[str, ...], fields: tuple[str, ...]) -> dict[str, object]: ...

