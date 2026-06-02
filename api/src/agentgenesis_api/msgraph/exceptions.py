"""Exceptions raised by the Microsoft Graph client.

Distinct types so graph nodes + routers can branch on cause:
- Transport errors → retry / mark run failed with a clear "Graph unreachable".
- Call errors      → arbitrary server-side failures; carry HTTP status so
                     routers can map cleanly (per red-team Finding 8).
- TranscriptNotReady → expected branch for Teams' async transcript processing;
  fetch_transcript node catches this and transitions to PENDING_TRANSCRIPT
  instead of failing the run.
"""


class MsGraphError(Exception):
    """Base for all Microsoft Graph client errors."""


class MsGraphTransportError(MsGraphError):
    """Connection / transport-level failure (Graph unreachable, network)."""


class MsGraphCallError(MsGraphError):
    """A Graph API call returned an error result.

    `status` carries the originating HTTP status code so callers can
    distinguish "user lacks permission" (403) from "Graph is down" (5xx)
    without string-matching the message. Per red-team Finding 8.

    `endpoint` is the URL or operation name that failed — used for logging.
    """

    def __init__(self, endpoint: str, message: str, status: int | None = None):
        super().__init__(f"{endpoint!r} failed: {message}")
        self.endpoint = endpoint
        self.message = message
        self.status = status


class TranscriptNotReady(MsGraphError):
    """Teams has not yet produced a transcript for this meeting."""

    def __init__(self, meeting_id: str):
        super().__init__(f"Transcript not ready for meeting {meeting_id!r}")
        self.meeting_id = meeting_id
