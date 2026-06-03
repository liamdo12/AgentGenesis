"""HTTP tests for the chat endpoints — SSE stream + history + restore + preview."""

import json
import time

from fastapi.testclient import TestClient

from agentgenesis_api.config import Settings
from agentgenesis_api.main import create_app


def _poll_until_done(client: TestClient, run_id: str, timeout_sec: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(0.05)
    raise AssertionError(f"Run {run_id} did not finish within {timeout_sec}s")


def _start_run_to_done(client: TestClient) -> str:
    resp = client.post("/runs", json={"meeting_id": "m-stub"})
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]
    _poll_until_done(client, run_id)
    return run_id


def _consume_sse(client: TestClient, run_id: str, message: str) -> list[tuple[str, str]]:
    """Drive POST /chat and return parsed (event, data) frames."""
    with client.stream(
        "POST",
        f"/runs/{run_id}/chat",
        json={"message": message},
    ) as resp:
        assert resp.status_code == 200, resp.read()
        buf = ""
        events: list[tuple[str, str]] = []
        for chunk in resp.iter_text():
            buf += chunk
            while "\n\n" in buf:
                frame, buf = buf.split("\n\n", 1)
                if not frame.strip() or frame.startswith(":"):
                    continue
                event = "message"
                data_lines: list[str] = []
                for line in frame.split("\n"):
                    if line.startswith("event:"):
                        event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[len("data:"):].strip())
                events.append((event, "\n".join(data_lines)))
        return events


def test_chat_conversational_only_no_revision(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _start_run_to_done(client)
        events = _consume_sse(client, run_id, "hello there")
        types = [e for e, _ in events]
        assert "text" in types
        assert "done" in types
        assert "revision" not in types
        assert "revision_preview" not in types

        done = next(d for e, d in events if e == "done")
        assert json.loads(done) == {"revision_version": None, "preview_id": None}


def test_chat_split_emits_single_revision(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _start_run_to_done(client)
        events = _consume_sse(client, run_id, "split AG-1002 into UI + API")
        types = [e for e, _ in events]
        assert "revision" in types
        rev = next(json.loads(d) for e, d in events if e == "revision")
        assert rev["version"] == 2
        assert rev["removed_ids"] == []
        ids = [s["id"] for s in rev["stories"]["stories"]]
        # Original AG-1002 was split, so we expect both new ids present.
        assert any("AG-1002" in i for i in ids)


def test_chat_bulk_delete_emits_preview(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _start_run_to_done(client)
        events = _consume_sse(
            client, run_id, "delete AG-1001, AG-1002"
        )
        types = [e for e, _ in events]
        assert "revision_preview" in types
        assert "revision" not in types
        preview = next(json.loads(d) for e, d in events if e == "revision_preview")
        assert set(preview["removed_ids"]) == {"AG-1001", "AG-1002"}

        # Accept the preview → commits the revision.
        r = client.post(
            f"/runs/{run_id}/chat/revisions/preview/{preview['preview_id']}/accept"
        )
        assert r.status_code == 200
        assert r.json()["version"] == 2

        # Accepting twice is 404 (preview consumed).
        r2 = client.post(
            f"/runs/{run_id}/chat/revisions/preview/{preview['preview_id']}/accept"
        )
        assert r2.status_code == 404


def test_chat_history_round_trip(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _start_run_to_done(client)
        _consume_sse(client, run_id, "first message")
        _consume_sse(client, run_id, "second message")
        # Background tasks finalize on response close; give them a tick.
        time.sleep(0.1)

        r = client.get(f"/runs/{run_id}/chat/history")
        assert r.status_code == 200
        turns = r.json()["turns"]
        assert len(turns) == 4  # 2 user + 2 assistant
        roles = [t["role"] for t in turns]
        assert roles == ["user", "assistant", "user", "assistant"]


def test_restore_reads_from_db(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _start_run_to_done(client)
        # Make a chat-rewrite (single delete) → v2
        _consume_sse(client, run_id, "delete AG-1001")
        # Now restore v1.
        r = client.post(f"/runs/{run_id}/chat/revisions/1/restore")
        assert r.status_code == 200
        body = r.json()
        assert body["restored_from"] == 1
        # Restore writes a forward revision so the next is v3.
        assert body["version"] == 3


def test_delete_chat_history(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        run_id = _start_run_to_done(client)
        _consume_sse(client, run_id, "hi")
        time.sleep(0.1)
        r = client.delete(f"/runs/{run_id}/chat/history")
        assert r.status_code == 200
        assert r.json()["deleted"] >= 1
        r = client.get(f"/runs/{run_id}/chat/history")
        assert r.json() == {"turns": []}


def test_chat_unknown_run_returns_404(env_setup) -> None:
    with TestClient(create_app(Settings())) as client:  # type: ignore[call-arg]
        r = client.get("/runs/nope/chat/history")
        assert r.status_code == 404
