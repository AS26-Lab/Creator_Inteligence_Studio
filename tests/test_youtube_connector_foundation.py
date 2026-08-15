from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from pathlib import Path

from creator_intelligence_studio.application.services.integration_service import IntegrationService
from creator_intelligence_studio.domain.integrations import (
    IntegrationAccountStatus,
    IntegrationCapability,
    IntegrationRateLimitState,
    IntegrationReadRequest,
)
from creator_intelligence_studio.domain.youtube_integration.services import READ_ONLY_SCOPES
from creator_intelligence_studio.infrastructure.integrations import IntegrationRegistry, YouTubeIntegrationConnector
from creator_intelligence_studio.infrastructure.youtube.analytics_api_client import YouTubeAnalyticsPage
from creator_intelligence_studio.infrastructure.youtube.data_api_client import YouTubeApiPage
from creator_intelligence_studio.infrastructure.youtube.oauth_client import OAuthAuthorizationResult, OAuthTokenResult
from creator_intelligence_studio.presentation.cli.integrations_cli import build_integrations_parser, handle_integrations_command
from creator_intelligence_studio.shared.dates import utc_now


class _FakeOAuthClient:
    def begin_authorization(self, *, client_id: str, scopes: tuple[str, ...], redirect_uri: str | None = None, state: str | None = None) -> OAuthAuthorizationResult:
        return OAuthAuthorizationResult(
            authorization_url=f"https://auth.local/start?client_id={client_id}&scope={' '.join(scopes)}",
            state=state or "state-1",
            redirect_uri=redirect_uri or "http://127.0.0.1:8765/callback",
        )

    def exchange_code(self, *, client_id: str, client_secret: str | None, code: str, redirect_uri: str) -> OAuthTokenResult:  # noqa: ARG002
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


def _build_connector(tmpdir: Path) -> YouTubeIntegrationConnector:
    return YouTubeIntegrationConnector(
        data_root=tmpdir / "youtube",
        credential_root=tmpdir / "credentials",
        environment="test",
        oauth_client=_FakeOAuthClient(),
        data_api_client=_FakeDataApiClient(),
        analytics_api_client=_FakeAnalyticsClient(),
    )


def _link_account(connector: YouTubeIntegrationConnector, creator_id: str = "creator-a"):
    result = connector.complete_authorization(
        creator_id=creator_id,
        authorization_code="authorization-code",
        client_id="client-1",
        client_secret="secret-1",
        redirect_uri="http://127.0.0.1:8765/callback",
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
        self.assertFalse(expired.success)
        self.assertEqual(expired.error.category.value, "authentication_expired")

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

            auth_start_args = parser.parse_args(["integrations", "youtube", "auth-start", "--creator-id", account.creator_id, "--json"])
            auth_start_code = handle_integrations_command(auth_start_args, service=service, stdout=stdout, stderr=stderr)
            stdout_value = stdout.getvalue()

            stdout = io.StringIO()
            account_args = parser.parse_args(["integrations", "youtube", "account", "--creator-id", account.creator_id, "--account-id", account.id, "--json"])
            account_code = handle_integrations_command(account_args, service=service, stdout=stdout, stderr=stderr)
            account_payload = json.loads(stdout.getvalue())

        self.assertEqual(auth_start_code, 0)
        self.assertIn("authorization_url", stdout_value)
        self.assertEqual(account_code, 0)
        self.assertTrue(account_payload["success"])
        self.assertEqual(account_payload["capability"], IntegrationCapability.ACCOUNT_PROFILE_READ.value)


if __name__ == "__main__":
    unittest.main()
