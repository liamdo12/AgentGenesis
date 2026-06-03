# Stub fixtures

Fixtures consumed by `AG_USE_STUB_NODES=1` so the API can run end-to-end without Microsoft Graph or Anthropic credentials.

## Required files

| File | Source | Purpose |
|---|---|---|
| `sample.mp4` | contributor downloads (gitignored) | Real video the stub `fetch_recording` copies into each run dir; ffmpeg extracts frames from this. |
| `sample.vtt` | `cp sample.example.vtt sample.vtt` (gitignored) | WebVTT transcript fed to `vtt_parser.parse()` by stub `fetch_transcript`. |
| `sample.example.vtt` | checked into repo | Reference transcript you can copy verbatim. |

## One-time setup

```bash
# 1. Copy the example transcript:
cp api/data/stub/sample.example.vtt api/data/stub/sample.vtt

# 2. Drop in a short H.264 mp4 (30-60s, 720p is plenty). Either:
#    a) Use a Creative-Commons clip you already have, OR
#    b) Fetch one of these public-domain samples:
curl -L -o api/data/stub/sample.mp4 \
  https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4
# or
curl -L -o api/data/stub/sample.mp4 \
  https://download.samplelib.com/mp4/sample-30s.mp4
```

If both URLs are dead, drop in any short mp4 you have — the stub pipeline only needs a real, decodable file. Don't commit it.

## VTT format

Hand-write your own if you want different topics in the canned summary. See `sample.example.vtt` for a minimal 6-cue example using the same dashboard + export themes the canned synthesis output references.

## Unplugging stub mode

When you no longer want stub support compiled into the API:

1. Delete `api/src/agentgenesis_api/services/stub.py`.
2. In `api/src/agentgenesis_api/main.py:_lifespan`, drop the `if settings.use_stub_nodes:` branch — always call `RealServices.create(...)`.
3. Optionally remove the `use_stub_nodes` field from `Settings`.

No graph node, builder, or runner code is touched — the stub provider was the only file with stub-specific logic.
