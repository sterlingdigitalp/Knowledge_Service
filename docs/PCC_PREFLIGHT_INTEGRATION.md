# PCC Preflight Integration

Knowledge_Service morning intelligence is a **stage** in the existing PCC Morning Preflight — not a separate scheduler.

## Existing Infrastructure

| Asset | Path |
|-------|------|
| Preflight script | `/Users/sterlingdigital/bin/pcc-morning-preflight.sh` |
| LaunchAgent | `~/Library/LaunchAgents/com.sterlingdigital.pcc-morning-preflight.plist` |
| Schedule | **06:26 local** (daily) |

## Integration Point

After Docker / SearXNG / Crawl4AI readiness checks, preflight invokes:

```bash
/Users/sterlingdigital/Knowledge_Service/bin/morning-intelligence.sh run --mode scheduled
```

## Preflight Sequence

```
06:26 LaunchAgent fires
  ↓
pcc-morning-preflight.sh
  ↓
Network connectivity check
  ↓
Docker Desktop + searxng + crawl4ai
  ↓
Knowledge_Service morning intelligence
  ↓
Preflight log summary line appended
```

## Logs

| Log | Purpose |
|-----|---------|
| `~/Library/Logs/pcc/morning-preflight.log` | Combined preflight + concise intelligence summary |
| `~/Library/Logs/pcc/morning-intelligence.log` | Structured per-run intelligence log |

## No Second Scheduler

`MorningBriefScheduler` remains for history tracking only. **launchd + PCC preflight** is the sole automation trigger.