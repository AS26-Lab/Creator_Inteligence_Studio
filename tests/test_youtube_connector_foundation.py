from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path
from datetime import timedelta
from urllib.error import HTTPError
from unittest.mock import patch

from creator_intelligence_studio.application.services.integration_service import IntegrationService
from creator_intelligence_studio.domain.integrations import (
    IntegrationAccountStatus,
    IntegrationCapability,
    IntegrationRateLimitState,
    IntegrationReadRequest,
)
from creator_intelligence_studio.domain.youtube_integration.errors import YouTubeAuthorizationError
from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES
from creator_intelligence_studio.infrastructure.integrations import IntegrationRegistry, YouTubeIntegrationConnector
from creator_intelligence_studio.infrastructure.youtube.analytics_api_client import YouTubeAnalyticsPage
from creator_intelligence_studio.infrastructure.youtube.credential_store import WindowsSecureCredentialStore
from creator_intelligence_studio.infrastructure.youtube.data_api_client import YouTubeApiPage
from creator_intelligence_studio.infrastructure.youtube.oauth_client import OAuthAuthorizationResult, OAuthTokenResult, OAuthFlowError, OAuthFlowStageOutcome
from creator_intelligence_studio.presentation.cli.integrations_cli import build_integrations_parser, handle_integrations_command
from creator_intelligence_studio.shared.dates import utc_now


class _FakeOAuthClient:
    def __init__(self) -> None:
        self.open_browser_calls: list[bool] = []

    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None, code_verifier: str | None = None) -> OAuthAuthorizationResult:
        return OAuthAuthorizationResult(
            authorization_url=f"https://auth.local/start?client_id={client_id}&scope={' '.join(scopes)}",
            state=state or "state-1",
            redirect_uri=redirect_uri or "http://127.0.0.1:8765/callback",
            code_verifier=code_verifier or "verifier-1",
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokenResult:  # noqa: ARG002
        return OAuthTokenResult(
            access_token="access-token-secret",
            refresh_token="refresh-token-secret",
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            google_account_identifier="google-account-1",
        )

    def refresh_token(self, *, client_id: str, client_secret: str | None, refresh_token: str) -> OAuthTokenResult:  # noqa: ARG002
        return OAuthTokenResult(
            access_token="refreshed-access-token",
            refresh_token="refresh-token-secret",
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=READ_ONLY_SCOPES,
            google_account_identifier="google-account-1",
        )

    def revoke(self, token: str) -> bool:  # noqa: ARG002
        return True

    def verify_token(self, token: str, scopes: tuple[str, ...]) -> dict[str, object]:  # noqa: ARG002
        return {"google_account_identifier": "google-account-1", "granted_scopes": scopes}

    def authorize_interactively(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True) -> tuple[OAuthAuthorizationResult, str]:  # noqa: ARG002
        result = self.begin_authorization(client_id=client_id, scopes=scopes)
        return result, "interactive-auth-code"

    def start_loopback_authorization(self, *, client_id: str, scopes: tuple[str, ...], open_browser: bool = True):  # noqa: ANN201, ARG002
        self.open_browser_calls.append(open_browser)
        result = self.begin_authorization(client_id=client_id, scopes=scopes)

        class _Session:
            def __init__(self, authorization: OAuthAuthorizationResult) -> None:
                self.authorization = authorization

            def wait_for_code(self, timeout: float = 120.0) -> str:  # noqa: ARG002
                return "interactive-auth-code"

            def close(self) -> None:
                return

        return _Session(result)


class _FailingExchangeOAuthClient(_FakeOAuthClient):
    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokenResult:  # noqa: ARG002
        raise OAuthFlowError(
            "OAuth token exchange failed.",
            stage="token_exchange_started",
            error_type="invalid_grant",
            http_status=400,
            error_description="invalid grant",
        )


class _MissingScopeOAuthClient(_FakeOAuthClient):
    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str, code_verifier: str | None = None) -> OAuthTokenResult:  # noqa: ARG002
        return OAuthTokenResult(
            access_token="access-token-secret",
            refresh_token="refresh-token-secret",
            token_type="Bearer",
            expires_in=3600,
            granted_scopes=("https://www.googleapis.com/auth/youtube.readonly",),
            google_account_identifier="google-account-1",
        )


class _FailingCredentialStore:
    def save(self, reference: str, bundle) -> None:  # noqa: ANN001, ARG002
        raise OSError("credential store unavailable")

    def load(self, reference: str):  # noqa: ANN001, ARG002
        return None

    def delete(self, reference: str) -> None:  # noqa: ARG002
        return None


class _MemoryCredentialStore:
    def __init__(self) -> None:
        self._values: dict[str, object] = {}

    def save(self, reference: str, bundle) -> None:  # noqa: ANN001
        self._values[reference] = bundle

    def load(self, reference: str):  # noqa: ANN001
        return self._values.get(reference)

    def delete(self, reference: str) -> None:  # noqa: ARG002
        self._values.pop(reference, None)


class _FailingDataApiClient:
    def list_channels(self, *, mine: bool = True, page_token: str | None = None, max_results: int = 50, part: str = "snippet,statistics,brandingSettings") -> YouTubeApiPage:  # noqa: ARG002
        raise HTTPError(
            "https://www.googleapis.com/youtube/v3/channels",
            403,
            "Forbidden",
            hdrs=None,
            fp=io.BytesIO(
                json.dumps(
                    {
                        "error": {
                            "code": 403,
                            "message": "Forbidden",
                            "errors": [{"reason": "insufficientPermissions"}],
                        }
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            ),
        )


class _RecoverableProfileDataApiClient:
    def __init__(self) -> None:
        self._delegate = None
        self.profile_attempts = 0

    def list_channels(self, *, mine: bool = True, page_token: str | None = None, max_results: int = 50, part: str = "snippet,statistics,brandingSettings") -> YouTubeApiPage:  # noqa: ARG002
        if part == "snippet,contentDetails":
            self.profile_attempts += 1
            if self.profile_attempts == 1:
                raise HTTPError(
                    "https://www.googleapis.com/youtube/v3/channels",
                    403,
                    "Forbidden",
                    hdrs=None,
                    fp=io.BytesIO(
                        json.dumps(
                            {
                                "error": {
                                    "code": 403,
                                    "message": "Forbidden",
                                    "errors": [{"reason": "insufficientPermissions"}],
                                }
                            },
                            ensure_ascii=False,
                                ).encode("utf-8")
                    ),
                )
        if self._delegate is None:
            self._delegate = _FakeDataApiClient()
        return self._delegate.list_channels(mine=mine, page_token=page_token, max_results=max_results, part=part)


class _FakeDataApiClient:
    def __init__(self, *, access_token: str | None = None) -> None:
        self.access_token = access_token

    def list_channels(self, *, mine: bool = True, page_token: str | None = None, max_results: int = 50, part: str = "snippet,statistics,brandingSettings") -> YouTubeApiPage:  # noqa: ARG002
        payload = {
            "items": [
                {
                    "id": "channel-1",
                    "snippet": {
                        "title": "Creator Uno 🎬",
                        "description": "Canal principal con emoji 🚀",
                        "publishedAt": "2023-01-01T00:00:00Z",
                        "country": "US",
                        "thumbnails": {"default": {"url": "https://img.local/channel-1.jpg"}},
                    },
                    "contentDetails": {"relatedPlaylists": {"uploads": "uploads-1"}},
                    "statistics": {"subscriberCount": "10", "videoCount": "2", "viewCount": "100"},
                    "brandingSettings": {"channel": {"customUrl": "@creatoruno"}},
                }
            ],
            "nextPageToken": None,
        }
        return YouTubeApiPage((payload["items"][0],), None, None, json.dumps(payload, ensure_ascii=False))

    def list_playlist_items(self, *, playlist_id: str, page_token: str | None = None, max_results: int = 50, part: str = "snippet,contentDetails,status") -> YouTubeApiPage:  # noqa: ARG002
        first_page = {
            "items": [
                {
                    "id": "playlist-item-1",
                    "snippet": {
                        "title": "Video uno 😊",
                        "description": "Descripcion uno 🎯",
                        "publishedAt": "2024-01-01T00:00:00Z",
                        "channelTitle": "Creator Uno",
                        "resourceId": {"videoId": "video-1"},
                        "thumbnails": {"default": {"url": "https://img.local/video-1.jpg"}},
                    },
                    "contentDetails": {"videoId": "video-1", "videoPublishedAt": "2024-01-01T00:00:00Z"},
                    "status": {"privacyStatus": "public"},
                },
                {
                    "id": "playlist-item-2",
                    "snippet": {
                        "title": "Video dos",
                        "description": "Descripcion dos",
                        "publishedAt": "2024-01-02T00:00:00Z",
                        "channelTitle": "Creator Uno",
                        "resourceId": {"videoId": "video-2"},
                        "thumbnails": {"default": {"url": "https://img.local/video-2.jpg"}},
                    },
                    "contentDetails": {"videoId": "video-2", "videoPublishedAt": "2024-01-02T00:00:00Z"},
                    "status": {"privacyStatus": "unlisted"},
                },
            ],
            "nextPageToken": "page-2",
        }
        second_page = {
            "items": [
                {
                    "id": "playlist-item-3",
                    "snippet": {
                        "title": "Video tres",
                        "description": "Descripcion tres",
                        "publishedAt": "2024-01-03T00:00:00Z",
                        "channelTitle": "Creator Uno",
                        "resourceId": {"videoId": "video-3"},
                        "thumbnails": {"default": {"url": "https://img.local/video-3.jpg"}},
                    },
                    "contentDetails": {"videoId": "video-3", "videoPublishedAt": "2024-01-03T00:00:00Z"},
                    "status": {"privacyStatus": "private"},
                }
            ],
            "nextPageToken": None,
        }
        payload = second_page if page_token == "page-2" else first_page
        return YouTubeApiPage(tuple(payload["items"]), payload["nextPageToken"], None, json.dumps(payload, ensure_ascii=False))

    def list_videos(self, *, channel_id: str | None = None, ids: tuple[str, ...] | None = None, page_token: str | None = None, max_results: int = 50, part: str = "snippet,contentDetails,statistics,status,topicDetails") -> YouTubeApiPage:  # noqa: ARG002
        items = []
        for video_id in ids or ():
            items.append(
                {
                    "id": video_id,
                    "snippet": {
                        "title": f"Titulo {video_id} ✨",
                        "description": f"Descripcion {video_id} 💡",
                        "publishedAt": "2024-01-10T00:00:00Z",
                        "thumbnails": {"default": {"url": f"https://img.local/{video_id}.jpg"}},
                    },
                    "contentDetails": {"duration": "PT5M0S"},
                    "status": {"privacyStatus": "public"},
                    "statistics": {"viewCount": "99", "likeCount": "9"},
                }
            )
        payload = {"items": items, "nextPageToken": None}
        return YouTubeApiPage(tuple(items), None, None, json.dumps(payload, ensure_ascii=False))


class _OptionalDataFailingClient(_FakeDataApiClient):
    def list_channels(self, *, mine: bool = True, page_token: str | None = None, max_results: int = 50, part: str = "snippet,statistics,brandingSettings") -> YouTubeApiPage:  # noqa: ARG002
        if part == "statistics,brandingSettings":
            raise HTTPError(
                "https://www.googleapis.com/youtube/v3/channels",
                403,
                "Forbidden",
                hdrs=None,
                fp=io.BytesIO(
                    json.dumps(
                        {
                            "error": {
                                "code": 403,
                                "message": "Forbidden",
                                "errors": [{"reason": "insufficientPermissions"}],
                            }
                        },
                        ensure_ascii=False,
                    ).encode("utf-8")
                ),
            )
        return super().list_channels(mine=mine, page_token=page_token, max_results=max_results, part=part)


class _FakeAnalyticsClient:
    def __init__(self, *, access_token: str | None = None) -> None:
        self.access_token = access_token

    def query(self, *, ids: str, metrics: str, dimensions: str | None = None, filters: str | None = None, start_date: str | None = None, end_date: str | None = None, max_results: int = 200, sort: str | None = None) -> YouTubeAnalyticsPage:  # noqa: ARG002
        payload = {
            "columnHeaders": [
                {"name": "video", "columnType": "DIMENSION"},
                {"name": "views", "columnType": "METRIC"},
                {"name": "likes", "columnType": "METRIC"},
            ],
            "rows": [["video-1", 123, 9]],
        }
        return YouTubeAnalyticsPage(rows=({"row": row} for row in payload["rows"]), raw_json=json.dumps(payload, ensure_ascii=False))


def _build_connector(
    tmpdir: Path,
    *,
    oauth_client: _FakeOAuthClient | None = None,
    data_api_client: _FakeDataApiClient | None = None,
    analytics_client: _FakeAnalyticsClient | None = None,
    credential_store=None,
) -> YouTubeIntegrationConnector:
    connector = YouTubeIntegrationConnector(
        data_root=tmpdir / "youtube",
        credential_root=tmpdir / "credentials",
        environment="test",
        client_id="client-1",
        oauth_client=oauth_client or _FakeOAuthClient(),
        data_api_client=data_api_client or _FakeDataApiClient(),
        analytics_api_client=analytics_client or _FakeAnalyticsClient(),
    )
    if credential_store is not None:
        connector._credential_store = credential_store
    return connector


def _link_account(connector: YouTubeIntegrationConnector, creator_id: str = "creator-a"):
    result = connector.complete_authorization(
        creator_id=creator_id,
        authorization_code="authorization-code",
        client_id="client-1",
        client_secret="secret-1",
        redirect_uri="http://127.0.0.1/callback",
        display_name="Creator Uno",
    )
    return result.account


class YouTubeConnectorFoundationTests(unittest.TestCase):
    def test_oauth_start_account_profile_and_content_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            start = connector.begin_authorization(creator_id="creator-a")
            account = _link_account(connector)
            service = IntegrationService(registry=IntegrationRegistry((connector,)))

            account_result = service.read(
                IntegrationReadRequest(
                    request_id="account-read",
                    creator_id=account.creator_id,
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.ACCOUNT_PROFILE_READ,
                    timestamp=utc_now(),
                )
            )

        self.assertEqual(start.scopes, READ_ONLY_SCOPES)
        self.assertIn("https://auth.local/start", start.authorization.authorization_url)
        self.assertEqual(account.connector_id, "youtube.connector")
        self.assertTrue(account_result.success)
        self.assertEqual(account_result.resources[0].title, "Creator Uno")
        self.assertIn("emoji 🚀", account_result.resources[0].description or "")

    def test_complete_authorization_records_successful_stage_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            result = connector.complete_authorization(
                creator_id="creator-a",
                authorization_code="authorization-code",
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="http://127.0.0.1/callback",
                display_name="Creator Uno",
            )

        diagnostics = result.diagnostics.to_dict()
        self.assertEqual(diagnostics["final_stage"], "auth_complete")
        self.assertEqual(diagnostics["failure_stage"], None)
        self.assertIn("credential_store_succeeded", [stage["stage"] for stage in diagnostics["stages"]])
        self.assertNotIn("access-token-secret", json.dumps(diagnostics, ensure_ascii=False))

    def test_complete_authorization_reports_token_exchange_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir), oauth_client=_FailingExchangeOAuthClient())
            with self.assertRaises(YouTubeAuthorizationError) as ctx:
                connector.complete_authorization(
                    creator_id="creator-a",
                    authorization_code="authorization-code",
                    client_id="client-1",
                    client_secret="secret-1",
                    redirect_uri="http://127.0.0.1/callback",
                    display_name="Creator Uno",
                )

        diagnostics = ctx.exception.diagnostics or {}
        self.assertEqual(diagnostics.get("failure_stage"), "token_exchange_started")
        self.assertEqual(diagnostics.get("error_type"), "invalid_grant")
        self.assertNotIn("access-token-secret", json.dumps(diagnostics, ensure_ascii=False))

    def test_complete_authorization_reports_missing_scope_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir), oauth_client=_MissingScopeOAuthClient())
            with self.assertRaises(YouTubeAuthorizationError) as ctx:
                connector.complete_authorization(
                    creator_id="creator-a",
                    authorization_code="authorization-code",
                    client_id="client-1",
                    client_secret="secret-1",
                    redirect_uri="http://127.0.0.1/callback",
                    display_name="Creator Uno",
                )

        diagnostics = ctx.exception.diagnostics or {}
        self.assertEqual(diagnostics.get("failure_stage"), "scope_validation_succeeded")
        self.assertIn("Missing scopes", diagnostics.get("error_description", ""))

    def test_complete_authorization_reports_credential_store_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = WindowsSecureCredentialStore()
            connector = _build_connector(Path(temp_dir), credential_store=store)
            with patch.object(store, "save", side_effect=OSError("credential store unavailable")):
                with self.assertRaises(YouTubeAuthorizationError) as ctx:
                    connector.complete_authorization(
                        creator_id="creator-a",
                        authorization_code="authorization-code",
                        client_id="client-1",
                        client_secret="secret-1",
                        redirect_uri="http://127.0.0.1/callback",
                        display_name="Creator Uno",
                    )

        diagnostics = ctx.exception.diagnostics or {}
        self.assertEqual(diagnostics.get("failure_stage"), "credential_store_started")
        self.assertEqual(diagnostics.get("backend"), "Windows Credential Manager")
        self.assertNotIn("access-token-secret", json.dumps(diagnostics, ensure_ascii=False))

    def test_complete_authorization_reports_profile_verification_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = _MemoryCredentialStore()
            connector = _build_connector(Path(temp_dir), data_api_client=_FailingDataApiClient(), credential_store=store)
            with self.assertRaises(YouTubeAuthorizationError) as ctx:
                connector.complete_authorization(
                    creator_id="creator-a",
                    authorization_code="authorization-code",
                    client_id="client-1",
                    client_secret="secret-1",
                    redirect_uri="http://127.0.0.1/callback",
                    display_name="Creator Uno",
                )

        diagnostics = ctx.exception.diagnostics or {}
        self.assertEqual(diagnostics.get("failure_stage"), "account_profile_verification_started")
        self.assertTrue(store._values)
        pending_accounts = connector.list_accounts("creator-a")
        self.assertEqual(len(pending_accounts), 1)
        self.assertIn(pending_accounts[0].status, {IntegrationAccountStatus.LINKING, IntegrationAccountStatus.ERROR})
        self.assertEqual(pending_accounts[0].metadata_summary.get("auth_state"), "authorized_pending_profile")
        self.assertIn("Forbidden", diagnostics.get("error_description", ""))
        self.assertEqual(diagnostics.get("error_type"), "insufficientPermissions")

    def test_recovery_reuses_stored_credential_after_profile_failure_without_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = _MemoryCredentialStore()
            data_api = _RecoverableProfileDataApiClient()
            connector = _build_connector(Path(temp_dir), data_api_client=data_api, credential_store=store)
            with self.assertRaises(YouTubeAuthorizationError):
                connector.complete_authorization(
                    creator_id="creator-a",
                    authorization_code="authorization-code",
                    client_id="client-1",
                    client_secret="secret-1",
                    redirect_uri="http://127.0.0.1/callback",
                    display_name="Creator Uno",
                )

            pending_accounts = connector.list_accounts("creator-a")
            self.assertEqual(len(pending_accounts), 1)
            pending_account = pending_accounts[0]
            self.assertIn(pending_account.status, {IntegrationAccountStatus.LINKING, IntegrationAccountStatus.ERROR})

            service = IntegrationService(registry=IntegrationRegistry((connector,)))
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="entity", required=True)
            build_integrations_parser(subparsers)
            stdout = io.StringIO()
            stderr = io.StringIO()

            auth_start_args = parser.parse_args(["integrations", "youtube", "auth-start", "--creator-id", "creator-a", "--client-id", "client-app-test", "--json"])
            auth_start_code = handle_integrations_command(auth_start_args, service=service, stdout=stdout, stderr=stderr)
            payload = json.loads(stdout.getvalue())

        self.assertEqual(auth_start_code, 0)
        self.assertTrue(payload["recovered_from_stored_credential"])
        self.assertTrue(payload["result"]["success"])
        self.assertFalse(connector._oauth_client.open_browser_calls)
        self.assertEqual(data_api.profile_attempts, 2)
        recovered_accounts = connector.list_accounts("creator-a")
        self.assertEqual(len(recovered_accounts), 1)
        self.assertEqual(recovered_accounts[0].status, IntegrationAccountStatus.CONNECTED)
        self.assertIsNotNone(store.load(recovered_accounts[0].credential_ref))

    def test_complete_authorization_ignores_optional_profile_enrichment_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = _MemoryCredentialStore()
            connector = _build_connector(Path(temp_dir), data_api_client=_OptionalDataFailingClient(), credential_store=store)
            result = connector.complete_authorization(
                creator_id="creator-a",
                authorization_code="authorization-code",
                client_id="client-1",
                client_secret="secret-1",
                redirect_uri="http://127.0.0.1/callback",
                display_name="Creator Uno",
            )

        self.assertEqual(result.diagnostics.final_stage, "auth_complete")
        self.assertTrue(store._values)

    def test_complete_authorization_reports_account_persistence_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = _MemoryCredentialStore()
            connector = _build_connector(Path(temp_dir), credential_store=store)
            with patch.object(connector._account_index, "upsert", side_effect=OSError("db write failed")):
                with self.assertRaises(YouTubeAuthorizationError) as ctx:
                    connector.complete_authorization(
                        creator_id="creator-a",
                        authorization_code="authorization-code",
                        client_id="client-1",
                        client_secret="secret-1",
                        redirect_uri="http://127.0.0.1/callback",
                        display_name="Creator Uno",
                    )

        diagnostics = ctx.exception.diagnostics or {}
        self.assertEqual(diagnostics.get("failure_stage"), "account_row_persisted")
        self.assertTrue(store._values)

    def test_content_and_analytics_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            account = _link_account(connector)
            service = IntegrationService(registry=IntegrationRegistry((connector,)))

            content_result = service.read(
                IntegrationReadRequest(
                    request_id="content-read",
                    creator_id=account.creator_id,
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.CONTENT_LIST_READ,
                    parameters={"page_token": None, "max_results": 2},
                    timestamp=utc_now(),
                )
            )
            video_result = service.read(
                IntegrationReadRequest(
                    request_id="video-read",
                    creator_id=account.creator_id,
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.CONTENT_METADATA_READ,
                    parameters={"video_ids": ["video-1"]},
                    timestamp=utc_now(),
                )
            )
            analytics_result = service.read(
                IntegrationReadRequest(
                    request_id="analytics-read",
                    creator_id=account.creator_id,
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.ANALYTICS_READ,
                    parameters={"start_date": "2024-01-01", "end_date": "2024-01-31", "metrics": ["views", "likes", "comments"], "video_id": "video-1"},
                    timestamp=utc_now(),
                )
            )

        self.assertTrue(content_result.success)
        self.assertEqual(len(content_result.resources), 2)
        self.assertEqual(content_result.next_page_token, "page-2")
        self.assertIn("😊", content_result.resources[0].title or "")
        self.assertEqual(video_result.resources[0].title, "Titulo video-1 ✨")
        self.assertIn("💡", video_result.resources[0].description or "")
        self.assertTrue(analytics_result.success)
        self.assertEqual([metric.metric_name for metric in analytics_result.analytics][:2], ["views", "likes"])
        self.assertTrue(any(metric.metric_name == "comments" and metric.availability == "missing" for metric in analytics_result.analytics))

    def test_creator_isolation_health_and_disconnect(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            account = _link_account(connector, creator_id="creator-a")
            service = IntegrationService(registry=IntegrationRegistry((connector,)))

            wrong_creator = service.read(
                IntegrationReadRequest(
                    request_id="owner-check",
                    creator_id="creator-b",
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.ACCOUNT_PROFILE_READ,
                    timestamp=utc_now(),
                )
            )
            health = connector.get_health(creator_id=account.creator_id, account_id=account.id)
            disconnected = connector.disconnect_account(creator_id=account.creator_id, account_id=account.id)

        self.assertFalse(wrong_creator.success)
        self.assertEqual(wrong_creator.error.category.value, "permission_denied")
        self.assertTrue(health.account_authenticated)
        self.assertTrue(disconnected)

    def test_status_overrides_rate_limit_and_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            account = _link_account(connector)
            service = IntegrationService(registry=IntegrationRegistry((connector,)))

            connector.set_rate_limit(account.id, IntegrationRateLimitState(limited=True, remaining=0, retry_after_seconds=30.0))
            rate_limited = service.read(
                IntegrationReadRequest(
                    request_id="rate-limit",
                    creator_id=account.creator_id,
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.CONTENT_LIST_READ,
                    timestamp=utc_now(),
                )
            )
            connector.set_rate_limit(account.id, None)
            connector.set_account_status(account.id, IntegrationAccountStatus.EXPIRED)
            expired = service.read(
                IntegrationReadRequest(
                    request_id="expired",
                    creator_id=account.creator_id,
                    connector_id=account.connector_id,
                    account_id=account.id,
                    capability=IntegrationCapability.CONTENT_LIST_READ,
                    timestamp=utc_now(),
                )
            )

        self.assertFalse(rate_limited.success)
        self.assertEqual(rate_limited.error.category.value, "rate_limited")
        self.assertTrue(rate_limited.rate_limit_state.limited)
        self.assertEqual(rate_limited.health.user_status.value, "quota_exhausted")
        self.assertFalse(expired.success)
        self.assertEqual(expired.error.category.value, "authentication_expired")
        self.assertEqual(expired.health.user_status.value, "auth_expired")

    def test_cli_youtube_commands_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            account = _link_account(connector)
            service = IntegrationService(registry=IntegrationRegistry((connector,)))
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="entity", required=True)
            build_integrations_parser(subparsers)
            stdout = io.StringIO()
            stderr = io.StringIO()

            auth_start_args = parser.parse_args(["integrations", "youtube", "auth-start", "--creator-id", account.creator_id, "--client-id", "client-app-test", "--json"])
            auth_start_code = handle_integrations_command(auth_start_args, service=service, stdout=stdout, stderr=stderr)
            stdout_value = stdout.getvalue()

            stdout = io.StringIO()
            auth_status_args = parser.parse_args(["integrations", "youtube", "auth-status", "--creator-id", account.creator_id, "--account-id", account.id, "--json"])
            auth_status_code = handle_integrations_command(auth_status_args, service=service, stdout=stdout, stderr=stderr)
            auth_status_payload = json.loads(stdout.getvalue())

            stdout = io.StringIO()
            account_args = parser.parse_args(["integrations", "youtube", "account", "--creator-id", account.creator_id, "--account-id", account.id, "--json"])
            account_code = handle_integrations_command(account_args, service=service, stdout=stdout, stderr=stderr)
            account_payload = json.loads(stdout.getvalue())

        self.assertEqual(auth_start_code, 1)
        self.assertFalse(connector._oauth_client.open_browser_calls)
        self.assertEqual(stdout_value.strip(), "")
        self.assertIn("conexion activa o pendiente", stderr.getvalue())
        self.assertEqual(auth_status_code, 0)
        self.assertEqual(auth_status_payload["health"]["user_status"], "connected")
        self.assertEqual(account_code, 0)
        self.assertTrue(account_payload["success"])
        self.assertEqual(account_payload["capability"], IntegrationCapability.ACCOUNT_PROFILE_READ.value)

    def test_cli_youtube_auth_start_refuses_when_connection_already_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            account = _link_account(connector)
            service = IntegrationService(registry=IntegrationRegistry((connector,)))
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="entity", required=True)
            build_integrations_parser(subparsers)
            stdout = io.StringIO()
            stderr = io.StringIO()

            auth_start_args = parser.parse_args(["integrations", "youtube", "auth-start", "--creator-id", account.creator_id, "--client-id", "client-app-test", "--json"])
            auth_start_code = handle_integrations_command(auth_start_args, service=service, stdout=stdout, stderr=stderr)

        self.assertEqual(auth_start_code, 1)
        self.assertFalse(connector._oauth_client.open_browser_calls)
        self.assertIn("conexion activa o pendiente", stderr.getvalue())

    def test_cli_youtube_auth_start_refuses_when_session_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            connector = _build_connector(Path(temp_dir))
            service = IntegrationService(registry=IntegrationRegistry((connector,)))
            session_dir = Path(temp_dir) / "youtube" / "auth_sessions"
            session_dir.mkdir(parents=True, exist_ok=True)
            (session_dir / "creator-a.json").write_text(
                json.dumps(
                    {
                        "creator_id": "creator-a",
                        "connector_id": "youtube.connector",
                        "status": "active",
                        "started_at": "2026-08-17T00:00:00+00:00",
                        "expires_at": (utc_now() + timedelta(minutes=10)).isoformat(),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(dest="entity", required=True)
            build_integrations_parser(subparsers)
            stdout = io.StringIO()
            stderr = io.StringIO()

            auth_start_args = parser.parse_args(["integrations", "youtube", "auth-start", "--creator-id", "creator-a", "--client-id", "client-app-test", "--json"])
            auth_start_code = handle_integrations_command(auth_start_args, service=service, stdout=stdout, stderr=stderr)

        self.assertEqual(auth_start_code, 1)
        self.assertFalse(connector._oauth_client.open_browser_calls)
        self.assertIn("sesion OAuth activa", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
