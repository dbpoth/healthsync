from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import anthropic
import os
import pathlib

app = FastAPI(title="HealthSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class DailyRecord(BaseModel):
    date: str
    rhr_dev: Optional[float]
    hrv_dev: Optional[float]
    drift: int

class InsightPayload(BaseModel):
    rhr_mean_dev: float
    hrv_mean_dev: float
    drift_score_avg: float
    days_flagged: int
    rhr_trend: str
    hrv_trend: str
    window_days: int
    date_range: str
    # for longitudinal per day data over last 14 days
    week1_rhr_dev: float
    week2_rhr_dev: float
    week1_hrv_dev: float
    week2_hrv_dev: float
    good_streak: int
    bad_streak: int
    daily: list[DailyRecord]


@app.post("/insight")
def insight(payload: InsightPayload):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "No API key configured.")
    client = anthropic.Anthropic(api_key=api_key)

    # build a readable daily table for Claude
    daily_lines = "\n".join(
        f"  {r.date}: RHR {'+' if (r.rhr_dev or 0) >= 0 else ''}{r.rhr_dev} bpm, "
        f"HRV {'+' if (r.hrv_dev or 0) >= 0 else ''}{r.hrv_dev} ms, "
        f"drift={r.drift}"
        for r in payload.daily
    )

    rhr_wow = payload.week2_rhr_dev - payload.week1_rhr_dev
    hrv_wow = payload.week2_hrv_dev - payload.week1_hrv_dev
    wow_summary = (
        f"RHR moved {'+' if rhr_wow >= 0 else ''}{rhr_wow:.1f} bpm week-over-week, "
        f"HRV moved {'+' if hrv_wow >= 0 else ''}{hrv_wow:.1f} ms week-over-week."
    )

    streak_summary = ""
    if payload.good_streak >= 3:
        streak_summary = f"Currently on a {payload.good_streak}-day clean streak (drift=0)."
    elif payload.bad_streak >= 3:
        streak_summary = f"Currently on a {payload.bad_streak}-day elevated drift streak."

    prompt = f"""You are HealthSync, a personal cardiovascular intelligence assistant. You're precise, warm, and speak directly to the user like you've been tracking their data for weeks — because you have.

Analysis window: {payload.date_range} ({payload.window_days} days)

DAILY BREAKDOWN:
{daily_lines}

SUMMARY:
- 14-day avg RHR deviation: {payload.rhr_mean_dev:+.2f} bpm from personal baseline
- 14-day avg HRV deviation: {payload.hrv_mean_dev:+.2f} ms from personal baseline
- RHR last 3 days: {payload.rhr_trend}
- HRV last 3 days: {payload.hrv_trend}
- Days flagged: {payload.days_flagged} of {payload.window_days}
- Avg drift score: {payload.drift_score_avg:.2f}/2.0
- Week-over-week: {wow_summary}
{f'- Streak: {streak_summary}' if streak_summary else ''}

Write 4-5 sentences as HealthSync. Structure it like this:
1. Lead with the most notable pattern in the data — streak, WoW shift, or trend. Be specific with numbers.
2. Explain what that pattern likely means in plain English (without naming medical conditions).
3. Note anything interesting or contrasting (e.g. RHR improving but HRV still low).
4. One specific, actionable suggestion based on what the data actually shows.

Rules:
- Use exact numbers from the data, not vague language
- Never say "it seems" or "may indicate" — be direct
- No diagnoses, no condition names
- Only suggest seeing a doctor if drift_score_avg > 1.5
- Speak in second person ("your RHR", "you've had")"""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
    except anthropic.OverloadedError:
        raise HTTPException(503, "AI service is temporarily busy — please try again in a moment.")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"AI service error: {e.message}")

    return {"insight": msg.content[0].text}

#     prompt = f"""You are a health intelligence assistant analyzing wearable data for a personal health tracking app.

# Data summary ({payload.window_days} days, {payload.date_range}):
# - Resting heart rate deviation from baseline: {payload.rhr_mean_dev} bpm
# - HRV deviation from baseline: {payload.hrv_mean_dev} ms
# - RHR trend (last 3 days): {payload.rhr_trend}
# - HRV trend (last 3 days): {payload.hrv_trend}
# - Days flagged: {payload.days_flagged} of {payload.window_days}
# - Avg drift score: {payload.drift_score_avg} (max 2.0)

# Write 3-5 sentences: what the data shows, anything worth noting, one actionable suggestion.
# Speak directly to the user. Calm, not alarmist. No diagnoses. No medical conditions named.
# Only suggest seeing a doctor if drift_score_avg > 1.5."""

#     msg = client.messages.create(
#         model="claude-sonnet-4-20250514",
#         max_tokens=300,
#         messages=[{"role": "user", "content": prompt}]
#     )
#     return {"insight": msg.content[0].text}

@app.get("/health")
def health():
    return {"status": "ok"}

_frontend = pathlib.Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")