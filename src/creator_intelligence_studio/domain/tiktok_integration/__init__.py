"""Dominio de la integracion oficial de solo lectura con TikTok."""

from .connection_types import (
    TikTokAccessLevel,
    TikTokConnectionStatus,
    TikTokLinkMethod,
    TikTokProductApprovalState,
    TikTokRemoteStatus,
)
from .entities import (
    TikTokConnection,
    TikTokContentLink,
    TikTokCoverVersion,
    TikTokMetricImport,
    TikTokMetricValue,
    TikTokProfile,
    TikTokRateLimitUsage,
    TikTokRemoteVideo,
    TikTokSyncItem,
    TikTokSyncReport,
    TikTokSyncRun,
    TikTokSyncSchedule,
    TikTokVideoTextVersion,
)
from .errors import (
    TikTokAuthorizationError,
    TikTokConnectionError,
    TikTokContentLinkError,
    TikTokIntegrationError,
    TikTokRateLimitError,
    TikTokSyncError,
)
from .metric_types import TikTokMetricScope, TikTokMetricSourceType, TikTokMetricStatus
from .repositories import TikTokIntegrationRepository
from .services import TikTokAuthProviderClient, TikTokDisplayApiClient
from .sync_types import TikTokSyncStatus, TikTokSyncType
from .value_objects import (
    DEFAULT_TIKTOK_API_VERSION,
    FORBIDDEN_WRITE_SCOPES,
    READ_ONLY_SCOPES,
    TikTokOAuthAuthorizationResult,
    TikTokOAuthTokenResult,
    TikTokProductApprovalSummary,
    TikTokRedirectValidationResult,
    build_tiktok_fingerprint,
    is_write_scope,
    normalize_scopes,
)

