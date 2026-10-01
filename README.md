# IBVAP — Intelligent Border Video Analytics Platform

Offline edge video analytics: cameras, YOLO, tracking, face, ANPR, configurable security rules.

## New in this build (non-integration)

- **Live alert badge** on top bar + beep on high/critical
- **Keyboard**: F5 refresh events, F6 Suspicious, F7 Events, Ctrl+A acknowledge newest
- **Events** category dropdown + CSV export
- **Unknown face** → suspicious (default rule, face quality filter)
- **Plate watchlist** (blacklist/whitelist) + **Plate Blacklist** rule
- **Line crossing** rule (first 2 zone points = line)
- **Schedule** hours on rules + **record on alert**
- **Rule templates** (Border Night / Gate Control / Crowd packs)
- **Dashboard** person / ANPR / unknown face / suspicious-new counters
- **Analytics** 24h heatmap + CSV export events/suspicious
- **Retention** job on startup (`storage.retention_days`)
- **Zones/lines** drawn on Live Monitor

## Quick start

```bash
cd IBVAP
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

If upgrading an old DB fails, delete `data/ibvap.db` once (schema auto-migrates best-effort).

## Shortcuts

| Key | Action |
|-----|--------|
| F5 | Refresh Events |
| F6 | Open Suspicious |
| F7 | Open Events |
| Ctrl+A | Acknowledge newest suspicious |

## License

Proprietary / Internal use.
