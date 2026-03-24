# HealthSync

**Longitudinal heart health intelligence for Apple Watch users.**

HealthSync analyzes your Apple Health data to establish your *personal* cardiovascular baseline, detect meaningful drift over time, and generate a plain-English weekly summary — powered by Claude AI.

**Live demo → [healthsync-p1ai.onrender.com](https://healthsync-p1ai.onrender.com)**

No Apple Watch? Hit "try with sample data" on the site to see a full demo instantly.

---

## What it does

Most people with Apple Watches accumulate months or years of heart data they never actually understand. HealthSync bridges that gap:

- Computes your **personal 30-day rolling baseline** for resting heart rate (RHR) and heart rate variability (HRV)
- Detects **sustained deviation** from that baseline — not just daily noise, but meaningful drift
- Scores each day with a **drift score (0–2)** based on how many metrics are flagged
- Generates a **plain-English AI insight** summarizing your last 14 days

## Privacy-first architecture

Your raw health data never leaves your device. All XML parsing, baseline computation, and drift scoring runs entirely in the browser. Only a small pre-computed statistical summary (8 numbers) is sent to the server to generate the AI insight.

```
Apple Health XML → parsed in YOUR browser
                 → baselines + drift computed locally  
                 → 8-number payload sent to server
                 → Claude generates insight → shown to you
```

## How to use

1. On your iPhone: Health app → profile photo → Export All Health Data
2. Unzip the downloaded file
3. Upload `export.xml` to [healthsync-p1ai.onrender.com](https://healthsync-p1ai.onrender.com)
4. See your personal baselines, drift chart, and AI weekly insight

## Tech stack

- **Frontend**: Vanilla JS + Chart.js — full pipeline runs in the browser
- **Backend**: FastAPI (Python) — single `/insight` endpoint, calls Claude API
- **AI**: Claude Sonnet via Anthropic API
- **Deploy**: Render

## Local development

```bash
# backend
cd backend
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn main:app --reload --port 8000

# frontend served automatically at http://localhost:8000
```

## What's next

HealthSync is Phase 1 of a larger vision: correlating cardiovascular data with calendar stress, travel, sleep, and activity to give people a truly longitudinal picture of how their life affects their heart — and vice versa. The goal is to make the kind of personalized health intelligence that used to require a clinical team accessible to anyone with a wearable device.

---

*Not a medical device. Does not diagnose or predict medical events.*
