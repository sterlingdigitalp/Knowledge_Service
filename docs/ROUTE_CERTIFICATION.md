# Route Certification Report

Evidence-backed acquisition route decisions for monitored sources. Latest runtime certification: `runtime_evidence/phase31_intelligence_20260701T010841Z`.

## Summary

| Source | Preferred route | Fallback chain | Status |
|--------|----------------|----------------|--------|
| All-In Podcast | `published_transcript` | youtube_transcript_api, yt_dlp_whisper | certified |
| Dwarkesh Podcast | `published_transcript` | youtube_transcript_api, yt_dlp_whisper | certified |
| Founders | `published_transcript` | youtube_transcript_api, yt_dlp_whisper | certified |
| Lex Fridman Podcast | `official_transcript` | youtube_transcript_api, yt_dlp_whisper | certified |
| The Peter Attia Drive | `published_transcript` | youtube_transcript_api, yt_dlp_whisper | certified |

## All-In Podcast (`all_in`)

- **Preferred route:** `published_transcript`
- **Evidence:** podscripts discovery URLs returned complete timestamped transcripts during runtime certification (67k+ chars)
- **Decision:** Discovery provides podscripts URLs; YouTube captions require a direct video URL and failed on podscripts targets

## Dwarkesh Podcast (`dwarkesh`)

- **Preferred route:** `published_transcript`
- **Evidence:** 1 runtime success on podscripts episode pages
- **Metrics:** complete transcript, timestamped segments, sub-second acquisition

## Founders (`founders`)

- **Preferred route:** `published_transcript`
- **Evidence:** podscripts mirror complete on configured index

## Lex Fridman Podcast (`lex_fridman`)

- **Preferred route:** `official_transcript`
- **Evidence:** acquisition ladder certified `lexfridman.com` official transcripts (400+ segments, 0.95 confidence)
- **Fallback:** YouTube captions when official URL unavailable

## The Peter Attia Drive (`peter_attia`)

- **Preferred route:** `published_transcript`
- **Evidence:** podscripts full-episode transcripts on configured discovery channel

## Regenerate

```bash
PYTHONPATH=src ./.venv/bin/python examples/certify_phase31_runtime.py
```

Produces `ROUTE_CERTIFICATION.md` under the new `runtime_evidence/phase31_intelligence_*` directory.