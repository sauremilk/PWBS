"""Zoom connector — OAuth2, Webhook-Receiver, Polling-Sync, Normalizer (TASK-053..055).

Implements User-Level OAuth2 for accessing Zoom Cloud Recording transcripts.
Zoom uses HTTP Basic Auth (base64(client_id:client_secret)) for the token
endpoint, similar to Notion.  Unlike Notion, Zoom *does* issue refresh tokens
with a finite access-token lifetime.

TASK-054 adds:
- Webhook payload validation (Pydantic models)
- HMAC-SHA256 signature verification for Zoom webhooks
- Transcript download from Zoom Cloud Recording API
- Polling-based ``fetch_since()`` via GET /users/me/recordings
- ``process_recording_completed()`` for webhook-driven ingestion
- Idempotency: duplicate recording_ids are skipped

TASK-055 adds:
- VTT → Plaintext parser with speaker attribution
- ``normalize()`` implementation (recordings → UnifiedDocument)
- Participant extraction from VTT speaker labels
- Metadata: duration_minutes, start_time, end_time, participant_count

References
----------
- https://developers.zoom.us/docs/integrations/oauth/
- https://developers.zoom.us/docs/api/rest/reference/zoom-api/methods/#tag/Cloud-Recording
- https://developers.zoom.us/docs/api/rest/webhook-reference/
- Architecture: D1 §3.1 (Connector table), PRD US-1.5 / F-007
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, SecretStr

from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncError, SyncResult
from pwbs.connectors.normalizer import normalize_document
from pwbs.connectors.oauth import OAuthTokens
from pwbs.core.config import get_settings
from pwbs.core.exceptions import ConnectorError, RateLimitError
from pwbs.schemas.enums import ContentType, SourceType

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.schemas.document import UnifiedDocument

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Zoom OAuth2 / API constants
# ---------------------------------------------------------------------------

_ZOOM_AUTH_URL = "https://zoom.us/oauth/authorize"
_ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
_ZOOM_API = "https://api.zoom.us/v2"
_HTTP_TIMEOUT = 30.0

# Scopes for reading cloud recording transcripts and meeting metadata
ZOOM_SCOPES = (
    "cloud_recording:read:list_user_recordings"
    " cloud_recording:read:list_recording_files"
    " meeting:read:list_meetings"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_rate_limit(response: httpx.Response) -> None:
    """Raise ``RateLimitError`` on HTTP 429."""
    if response.status_code == 429:  # noqa: PLR2004
        retry_after = int(response.headers.get("Retry-After", "60"))
        raise RateLimitError(
            f"Zoom API rate limited: {response.text}",
            status_code=429,
            retry_after=retry_after,
        )


# ---------------------------------------------------------------------------
# Webhook Pydantic models (TASK-054)
# ---------------------------------------------------------------------------


class ZoomRecordingFile(BaseModel):
    """A single file within a Zoom cloud recording."""

    id: str
    recording_type: str  # e.g. "audio_transcript", "shared_screen_with_speaker_view"
    file_type: str  # "TRANSCRIPT", "MP4", "M4A", "CHAT", ...
    download_url: str = ""
    status: str = ""
    file_size: int = 0
    recording_start: str = ""
    recording_end: str = ""


class ZoomRecordingObject(BaseModel):
    """The ``object`` inside a Zoom recording webhook payload."""

    uuid: str
    id: int
    topic: str = ""
    start_time: str = ""
    duration: int = 0
    recording_files: list[ZoomRecordingFile] = []


class ZoomWebhookPayload(BaseModel):
    """The ``payload`` of a Zoom webhook event."""

    account_id: str = ""
    object: ZoomRecordingObject


class ZoomWebhookEvent(BaseModel):
    """Top-level Zoom webhook event envelope."""

    event: str  # "recording.completed", "endpoint.url_validation"
    payload: ZoomWebhookPayload | None = None
    event_ts: int | None = None

    # URL validation challenge fields
    class UrlValidationPayload(BaseModel):
        plainToken: str  # noqa: N815 — Zoom's field name

    # For endpoint.url_validation events
    url_validation_payload: UrlValidationPayload | None = None


# ---------------------------------------------------------------------------
# Webhook signature verification (TASK-054)
# ---------------------------------------------------------------------------


def validate_zoom_webhook_signature(
    *,
    request_body: bytes,
    timestamp: str,
    signature: str,
    secret: str,
) -> bool:
    """Verify a Zoom webhook signature (HMAC-SHA256).

    Zoom signs webhooks with::

        v0:{timestamp}:{request_body}

    using HMAC-SHA256 with the webhook secret token.  The resulting hex
    digest is prefixed with ``v0=``.

    Parameters
    ----------
    request_body:
        Raw request body bytes.
    timestamp:
        Value of the ``x-zm-request-timestamp`` header.
    signature:
        Value of the ``x-zm-signature`` header (e.g. ``v0=abc123...``).
    secret:
        The Zoom webhook secret token from app configuration.

    Returns
    -------
    bool
        ``True`` if the signature is valid.
    """
    message = f"v0:{timestamp}:{request_body.decode()}"
    expected = (
        "v0="
        + hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
    )
    return hmac.compare_digest(expected, signature)


def compute_url_validation_response(
    plain_token: str,
    secret: str,
) -> dict[str, str]:
    """Compute the response for Zoom's URL validation challenge.

    Returns a dict with ``plainToken`` and ``encryptedToken`` suitable
    for returning as JSON from the webhook endpoint.
    """
    encrypted = hmac.new(
        secret.encode(),
        plain_token.encode(),
        hashlib.sha256,
    ).hexdigest()
    return {"plainToken": plain_token, "encryptedToken": encrypted}


# ---------------------------------------------------------------------------
# Cursor helpers (TASK-054)
# ---------------------------------------------------------------------------


def _encode_recordings_cursor(
    *,
    watermark: str,
    next_page_token: str | None = None,
) -> str:
    """Encode a recordings sync cursor.

    The watermark is an ISO date string (``YYYY-MM-DD``).  When paginating,
    the ``next_page_token`` from Zoom's response is included.
    """
    if next_page_token:
        return json.dumps(
            {"watermark": watermark, "next_page_token": next_page_token},
            separators=(",", ":"),
        )
    return watermark


def _decode_recordings_cursor(cursor: str) -> tuple[str | None, str | None]:
    """Decode a cursor into ``(watermark, next_page_token)``.

    Returns ``(None, None)`` for an empty/initial cursor.
    """
    if not cursor:
        return None, None
    if cursor.startswith("{"):
        try:
            data = json.loads(cursor)
            return data.get("watermark"), data.get("next_page_token")
        except json.JSONDecodeError:
            return cursor, None
    return cursor, None


# ---------------------------------------------------------------------------
# VTT parsing helpers (TASK-055)
# ---------------------------------------------------------------------------

# Matches a VTT timestamp line: "00:00:01.000 --> 00:00:05.000"
_VTT_TIMESTAMP_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}",
)

# Matches an SRT timestamp line: "00:00:01,000 --> 00:00:05,000"
_SRT_TIMESTAMP_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}",
)

# Same pattern without ^ anchor, for content sniffing via re.search
_SRT_TIMESTAMP_SEARCH_RE = re.compile(
    r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}",
)


def _parse_vtt(vtt_content: str) -> tuple[str, list[str]]:
    """Parse a VTT transcript into plaintext with speaker labels.

    Zoom VTT transcripts have the format::

        WEBVTT

        1
        00:00:01.000 --> 00:00:05.000
        Speaker Name: Hello everyone.

        2
        00:00:05.000 --> 00:00:10.000
        Another Speaker: Thanks for joining.

    Parameters
    ----------
    vtt_content:
        Raw VTT file content.

    Returns
    -------
    tuple[str, list[str]]
        - Cleaned plaintext (speaker labels preserved for attribution).
        - List of unique speaker names extracted from the transcript.
    """
    lines: list[str] = []
    speakers: set[str] = set()

    for line in vtt_content.splitlines():
        stripped = line.strip()

        # Skip WEBVTT header, blank lines, and numeric cue identifiers
        if not stripped:
            continue
        if stripped == "WEBVTT":
            continue
        if stripped.isdigit():
            continue
        # Skip timestamp lines
        if _VTT_TIMESTAMP_RE.match(stripped):
            continue

        # Extract speaker name if present ("Speaker: text")
        colon_idx = stripped.find(": ")
        if colon_idx > 0:
            potential_speaker = stripped[:colon_idx].strip()
            # Speaker names are typically short and don't contain timestamps
            if (
                len(potential_speaker) < 100  # noqa: PLR2004
                and not _VTT_TIMESTAMP_RE.match(potential_speaker)
                and not potential_speaker.isdigit()
            ):
                speakers.add(potential_speaker)

        lines.append(stripped)

    plaintext = "\n".join(lines)
    # Sort speakers for deterministic output
    return plaintext, sorted(speakers)


def _parse_srt(srt_content: str) -> tuple[str, list[str]]:
    """Parse an SRT transcript into plaintext with speaker labels.

    SRT transcripts have the format::

        1
        00:00:01,000 --> 00:00:05,000
        Speaker Name: Hello everyone.

        2
        00:00:05,000 --> 00:00:10,000
        Another Speaker: Thanks for joining.

    Parameters
    ----------
    srt_content:
        Raw SRT file content.

    Returns
    -------
    tuple[str, list[str]]
        - Cleaned plaintext (speaker labels preserved for attribution).
        - List of unique speaker names extracted from the transcript.
    """
    lines: list[str] = []
    speakers: set[str] = set()

    for line in srt_content.splitlines():
        stripped = line.strip()

        if not stripped:
            continue
        if stripped.isdigit():
            continue
        if _SRT_TIMESTAMP_RE.match(stripped):
            continue

        colon_idx = stripped.find(": ")
        if colon_idx > 0:
            potential_speaker = stripped[:colon_idx].strip()
            if (
                len(potential_speaker) < 100  # noqa: PLR2004
                and not _SRT_TIMESTAMP_RE.match(potential_speaker)
                and not potential_speaker.isdigit()
            ):
                speakers.add(potential_speaker)

        lines.append(stripped)

    plaintext = "\n".join(lines)
    return plaintext, sorted(speakers)


def detect_transcript_format(content: str, filename: str) -> str:
    """Detect transcript format from filename extension or content sniffing.

    Returns ``"vtt"``, ``"srt"``, or ``"txt"``.
    """
    lower_name = filename.lower() if filename else ""

    if lower_name.endswith(".vtt"):
        return "vtt"
    if lower_name.endswith(".srt"):
        return "srt"
    if lower_name.endswith(".txt"):
        # Content sniffing for .txt files that are actually VTT/SRT
        if content.strip().startswith("WEBVTT"):
            return "vtt"
        if _SRT_TIMESTAMP_SEARCH_RE.search(content[:500]):
            return "srt"
        return "txt"

    # Fallback: content sniffing
    if content.strip().startswith("WEBVTT"):
        return "vtt"
    if _SRT_TIMESTAMP_SEARCH_RE.search(content[:500]):
        return "srt"
    return "txt"


def parse_transcript(content: str, filename: str) -> tuple[str, list[str]]:
    """Parse a transcript file, auto-detecting format.

    Supports VTT, SRT, and plain text formats.

    Parameters
    ----------
    content:
        Raw file content as string.
    filename:
        Original filename (used for format detection via extension).

    Returns
    -------
    tuple[str, list[str]]
        - Cleaned plaintext content.
        - List of unique speaker names (empty for plain text).
    """
    fmt = detect_transcript_format(content, filename)
    if fmt == "vtt":
        return _parse_vtt(content)
    if fmt == "srt":
        return _parse_srt(content)
    return content.strip(), []


def _extract_participants_from_files(
    recording_files: list[dict[str, object]],
) -> list[str]:
    """Extract participant names/emails from recording file metadata.

    Zoom ``participant_audio_files`` include per-participant info.  This
    function gathers unique names from the ``file_name`` or ``user_name``
    fields.
    """
    participants: set[str] = set()
    for rf in recording_files:
        if not isinstance(rf, dict):
            continue
        # participant_audio_files have user_name / user_email
        user_name = rf.get("user_name")
        user_email = rf.get("user_email")
        if isinstance(user_email, str) and user_email:
            participants.add(user_email)
        elif isinstance(user_name, str) and user_name:
            participants.add(user_name)
        # file_name can also contain participant names
        file_name = rf.get("file_name")
        if (
            isinstance(file_name, str)
            and file_name
            and rf.get("recording_type") == "participant_audio"
        ):
            participants.add(file_name)
    return sorted(participants)


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------


class ZoomConnector(BaseConnector):
    """Connector for Zoom cloud recordings and meeting transcripts.

    Class methods ``build_auth_url`` and ``exchange_code`` handle the OAuth2
    flow.  The resulting ``OAuthTokens`` must be encrypted via
    ``encrypt_tokens`` and stored in the ``connections`` table by the API
    layer (TASK-087).

    For sync and normalization (TASK-054, TASK-055), pass the decrypted
    ``access_token`` in ``config.extra["access_token"]`` when instantiating
    the connector.
    """

    source_type: SourceType = SourceType.ZOOM

    def __init__(
        self,
        *,
        owner_id: UUID,
        connection_id: UUID,
        config: ConnectorConfig,
    ) -> None:
        super().__init__(
            owner_id=owner_id,
            connection_id=connection_id,
            config=config,
        )
        # Idempotency: track processed recording UUIDs per connector instance
        self._processed_recording_ids: set[str] = set()

    # ------------------------------------------------------------------
    # OAuth2 helpers (stateless — no instance required)
    # ------------------------------------------------------------------

    @staticmethod
    def build_auth_url(*, redirect_uri: str, state: str) -> str:
        """Generate the Zoom OAuth2 authorization URL.

        Parameters
        ----------
        redirect_uri:
            Where Zoom redirects after user consent.
        state:
            Opaque CSRF-protection value.

        Returns
        -------
        str
            Full authorization URL the frontend should redirect to.

        Raises
        ------
        ConnectorError
            If ``zoom_client_id`` is not configured.
        """
        settings = get_settings()
        client_id = settings.zoom_client_id
        if not client_id:
            raise ConnectorError(
                "zoom_client_id is not configured",
                code="ZOOM_MISSING_CLIENT_ID",
            )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{_ZOOM_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(
        *,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """Exchange an OAuth2 authorization code for access + refresh tokens.

        Zoom uses HTTP Basic Auth (base64(client_id:client_secret)) for the
        token endpoint — the same pattern as Notion.

        Parameters
        ----------
        code:
            The authorization code from the OAuth2 callback.
        redirect_uri:
            Must match the redirect_uri used in ``build_auth_url``.

        Returns
        -------
        OAuthTokens
            Token data with ``access_token``, ``refresh_token``, and
            ``expires_at``.

        Raises
        ------
        ConnectorError
            On network errors, invalid codes, or missing credentials.
        """
        settings = get_settings()
        client_id = settings.zoom_client_id
        client_secret = settings.zoom_client_secret.get_secret_value()
        if not client_id or not client_secret:
            raise ConnectorError(
                "zoom_client_id / zoom_client_secret not configured",
                code="ZOOM_MISSING_CREDENTIALS",
            )

        # Zoom requires Basic Auth: base64(client_id:client_secret)
        credentials = base64.b64encode(
            f"{client_id}:{client_secret}".encode(),
        ).decode()

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.post(
                    _ZOOM_TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Zoom token exchange network error: {exc}",
                code="ZOOM_NETWORK_ERROR",
            ) from exc

        _raise_for_rate_limit(response)

        if response.status_code != 200:  # noqa: PLR2004
            error_body: dict[str, str] = {}
            try:
                error_body = response.json()
            except Exception:  # noqa: BLE001
                pass
            error_reason = error_body.get(
                "reason",
                error_body.get("error", f"HTTP {response.status_code}"),
            )
            logger.warning(
                "Zoom OAuth code exchange failed: HTTP %d — %s",
                response.status_code,
                error_reason,
            )
            raise ConnectorError(
                f"Zoom OAuth code exchange failed: {error_reason}",
                code="ZOOM_TOKEN_EXCHANGE_FAILED",
            )

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ConnectorError(
                "Zoom token response missing access_token",
                code="ZOOM_MISSING_ACCESS_TOKEN",
            )

        expires_in = data.get("expires_in")
        expires_at = time.time() + float(expires_in) if expires_in else None
        refresh_token_value = data.get("refresh_token")

        return OAuthTokens(
            access_token=SecretStr(access_token),
            refresh_token=(SecretStr(refresh_token_value) if refresh_token_value else None),
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
            scope=data.get("scope", ZOOM_SCOPES),
        )

    # ------------------------------------------------------------------
    # Instance helpers
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """Extract the Zoom access token from ``config.extra``."""
        token = self.config.extra.get("access_token")
        if not token or not isinstance(token, str):
            raise ConnectorError(
                "Missing access_token in connector config.extra",
                code="ZOOM_MISSING_TOKEN",
            )
        return token

    # ------------------------------------------------------------------
    # Transcript download (TASK-054)
    # ------------------------------------------------------------------

    async def fetch_transcript(self, download_url: str) -> str:
        """Download a transcript file from Zoom Cloud Recording API.

        Parameters
        ----------
        download_url:
            The ``download_url`` from a recording file with
            ``file_type == "TRANSCRIPT"``.

        Returns
        -------
        str
            Raw transcript content (typically VTT format).

        Raises
        ------
        ConnectorError
            On network errors or non-200 responses.
        """
        access_token = self._get_access_token()

        try:
            async with httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    download_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Zoom transcript download network error: {exc}",
                code="ZOOM_TRANSCRIPT_NETWORK_ERROR",
            ) from exc

        _raise_for_rate_limit(response)

        if response.status_code != 200:  # noqa: PLR2004
            raise ConnectorError(
                f"Zoom transcript download failed: HTTP {response.status_code}",
                code="ZOOM_TRANSCRIPT_DOWNLOAD_FAILED",
            )

        return response.text

    # ------------------------------------------------------------------
    # BaseConnector abstract methods
    # ------------------------------------------------------------------

    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Fetch Zoom recordings since *cursor* (polling).

        - ``cursor=None`` → **initial sync**: fetches recordings from the
          last 30 days.
        - ``cursor=<date>`` → **incremental sync**: fetches recordings
          from that date onward.

        For each recording, transcript files are downloaded, parsed to
        plaintext via ``normalize()``, and returned as ``UnifiedDocument``
        objects.

        Returns a ``SyncResult`` with normalised documents, errors, and the
        new cursor.
        """
        access_token = self._get_access_token()

        watermark, page_token = _decode_recordings_cursor(cursor or "")

        # Default to 30 days back for initial sync
        if not watermark:
            watermark = (datetime.now(tz=timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

        params: dict[str, str | int] = {
            "from": watermark,
            "to": today,
            "page_size": min(self.config.max_batch_size, 300),
        }
        if page_token:
            params["next_page_token"] = page_token

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_ZOOM_API}/users/me/recordings",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )
        except httpx.RequestError as exc:
            raise ConnectorError(
                f"Zoom recordings API network error: {exc}",
                code="ZOOM_RECORDINGS_NETWORK_ERROR",
            ) from exc

        _raise_for_rate_limit(response)

        if response.status_code != 200:  # noqa: PLR2004
            raise ConnectorError(
                f"Zoom recordings API error: HTTP {response.status_code} — {response.text}",
                code="ZOOM_RECORDINGS_API_ERROR",
            )

        data = response.json()
        meetings: list[dict[str, object]] = data.get("meetings", [])
        next_page = data.get("next_page_token", "")

        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []

        for meeting in meetings:
            meeting_uuid = str(meeting.get("uuid", ""))
            if not meeting_uuid:
                continue

            # Skip already-processed recordings (idempotency)
            if meeting_uuid in self._processed_recording_ids:
                continue

            recording_files = meeting.get("recording_files", [])
            if not isinstance(recording_files, list):
                continue

            # Find transcript files
            transcript_url: str | None = None
            for rf in recording_files:
                if not isinstance(rf, dict):
                    continue
                if str(rf.get("file_type", "")).upper() == "TRANSCRIPT":
                    transcript_url = str(rf.get("download_url", ""))
                    break

            if not transcript_url:
                continue  # No transcript for this recording

            # Download transcript
            try:
                transcript_content = await self.fetch_transcript(transcript_url)
            except (ConnectorError, RateLimitError) as exc:
                errors.append(
                    SyncError(
                        source_id=meeting_uuid,
                        error=f"Transcript download failed: {exc}",
                    )
                )
                continue

            # Build raw dict for normalize()
            raw: dict[str, object] = {
                "uuid": meeting_uuid,
                "id": meeting.get("id", 0),
                "topic": meeting.get("topic", ""),
                "start_time": meeting.get("start_time", ""),
                "duration": meeting.get("duration", 0),
                "transcript": transcript_content,
                "recording_files": recording_files,
            }

            try:
                doc = self.normalize(raw)  # type: ignore[arg-type]
                documents.append(doc)
                self._processed_recording_ids.add(meeting_uuid)
            except Exception as exc:  # noqa: BLE001
                errors.append(
                    SyncError(
                        source_id=meeting_uuid,
                        error=f"Normalization failed: {exc}",
                    )
                )

        has_more = bool(next_page)
        new_cursor = _encode_recordings_cursor(
            watermark=today if not has_more else watermark,
            next_page_token=next_page if has_more else None,
        )

        return SyncResult(
            documents=documents,
            new_cursor=new_cursor,
            errors=errors,
            has_more=has_more,
        )

    def normalize(self, raw: dict[str, object]) -> UnifiedDocument:
        """Normalize a Zoom recording/transcript into a UnifiedDocument.

        Expects the *raw* dict built by ``fetch_since()`` or
        ``process_recording_completed()`` with at least::

            {
                "uuid": "meeting-uuid",
                "topic": "Meeting title",
                "start_time": "2026-01-15T10:00:00Z",
                "duration": 30,
                "transcript": "WEBVTT\\n\\n...",
                "recording_files": [...],
            }

        The VTT transcript is parsed into plaintext with speaker labels
        preserved.  Speaker names serve as participants alongside any
        participant info in ``recording_files``.
        """
        meeting_uuid = str(raw.get("uuid", ""))
        if not meeting_uuid:
            raise ConnectorError(
                "Raw recording data missing 'uuid'",
                code="ZOOM_MISSING_UUID",
            )

        topic = str(raw.get("topic", "")) or "(Kein Titel)"
        transcript_raw = raw.get("transcript", "")
        transcript_str = str(transcript_raw) if transcript_raw else ""

        # Parse VTT → plaintext + speakers
        if transcript_str.strip():
            content, vtt_speakers = _parse_vtt(transcript_str)
        else:
            content = ""
            vtt_speakers = []

        # Collect participants from VTT speakers + recording files
        recording_files = raw.get("recording_files", [])
        file_participants: list[str] = []
        if isinstance(recording_files, list):
            file_participants = _extract_participants_from_files(
                recording_files,  # type: ignore[arg-type]
            )

        # Merge and deduplicate, preferring file-based (emails) over VTT names
        all_participants = sorted(
            set(file_participants) | set(vtt_speakers),
        )

        # Parse timestamps
        start_time_str = str(raw.get("start_time", ""))
        duration = raw.get("duration", 0)
        duration_minutes = int(duration) if isinstance(duration, (int, float)) else 0

        created_at: datetime | None = None
        if start_time_str:
            try:
                created_at = datetime.fromisoformat(
                    start_time_str.replace("Z", "+00:00"),
                )
            except ValueError:
                pass

        # Compute end_time from start + duration
        end_time_str = ""
        if created_at and duration_minutes > 0:
            end_time = created_at + timedelta(minutes=duration_minutes)
            end_time_str = end_time.isoformat()

        metadata: dict[str, str | int | list[str]] = {
            "duration_minutes": duration_minutes,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "participant_count": len(all_participants),
        }
        if vtt_speakers:
            metadata["speakers"] = vtt_speakers

        return normalize_document(
            owner_id=self.owner_id,
            source_type=SourceType.ZOOM,
            source_id=meeting_uuid,
            title=topic,
            content=content,
            content_type=ContentType.PLAINTEXT,
            metadata=metadata,  # type: ignore[arg-type]
            participants=all_participants,
            created_at=created_at,
        )

    # ------------------------------------------------------------------
    # Webhook-driven ingestion (TASK-054)
    # ------------------------------------------------------------------

    async def process_recording_completed(
        self,
        event: ZoomWebhookEvent,
    ) -> SyncResult:
        """Handle a ``recording.completed`` webhook event.

        Extracts transcript files from the event payload, downloads them,
        and returns a ``SyncResult``.  Idempotent: duplicate ``uuid`` values
        are silently skipped.

        Parameters
        ----------
        event:
            Parsed and validated Zoom webhook event.

        Returns
        -------
        SyncResult
            Normalised documents or errors for each recording.
        """
        if event.payload is None:
            return SyncResult()

        recording = event.payload.object
        meeting_uuid = recording.uuid

        # Idempotency: skip already-processed recordings
        if meeting_uuid in self._processed_recording_ids:
            logger.info(
                "Skipping duplicate recording %s (already processed)",
                meeting_uuid,
            )
            return SyncResult()

        documents: list[UnifiedDocument] = []
        errors: list[SyncError] = []

        # Find transcript files
        transcript_url: str | None = None
        for rf in recording.recording_files:
            if rf.file_type.upper() == "TRANSCRIPT":
                transcript_url = rf.download_url
                break

        if not transcript_url:
            logger.info(
                "Recording %s has no transcript file — skipping",
                meeting_uuid,
            )
            return SyncResult()

        # Download transcript
        try:
            transcript_content = await self.fetch_transcript(transcript_url)
        except (ConnectorError, RateLimitError) as exc:
            errors.append(
                SyncError(
                    source_id=meeting_uuid,
                    error=f"Transcript download failed: {exc}",
                )
            )
            return SyncResult(errors=errors)

        raw: dict[str, object] = {
            "uuid": meeting_uuid,
            "id": recording.id,
            "topic": recording.topic,
            "start_time": recording.start_time,
            "duration": recording.duration,
            "transcript": transcript_content,
            "recording_files": [rf.model_dump() for rf in recording.recording_files],
        }

        try:
            doc = self.normalize(raw)  # type: ignore[arg-type]
            documents.append(doc)
            self._processed_recording_ids.add(meeting_uuid)
        except Exception as exc:  # noqa: BLE001
            errors.append(
                SyncError(
                    source_id=meeting_uuid,
                    error=f"Normalization failed: {exc}",
                )
            )

        return SyncResult(documents=documents, errors=errors)

    async def health_check(self) -> bool:
        """Verify the Zoom API is reachable with stored credentials.

        Makes a lightweight GET to the ``/users/me`` endpoint.
        """
        access_token = self.config.extra.get("access_token")
        if not access_token or not isinstance(access_token, str):
            logger.warning(
                "Health check skipped — no access_token in config.extra: connection_id=%s",
                self.connection_id,
            )
            return False

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                response = await client.get(
                    f"{_ZOOM_API}/users/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                _raise_for_rate_limit(response)
                return response.status_code == 200  # noqa: PLR2004
        except httpx.RequestError:
            logger.warning(
                "Health check failed — network error: connection_id=%s",
                self.connection_id,
                exc_info=True,
            )
            return False
