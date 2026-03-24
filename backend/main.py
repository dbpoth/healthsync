from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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


# ── Request model ────────────────────────────────────────────────────────────
# This is the only thing the server ever receives — a tiny structured summary.
# Raw health data never leaves the user's device.

class InsightPayload(BaseModel):
    rhr_mean_dev:    float
    hrv_mean_dev:    float
    drift_score_avg: float
    days_flagged:    int
    rhr_trend:       str   # "up" | "down" | "stable"
    hrv_trend:       str
    window_days:     int
    date_range:      str


# ── AI insight ───────────────────────────────────────────────────────────────

def generate_health_insight(payload: InsightPayload) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "No API key set — add ANTHROPIC_API_KEY to your environment."

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are a health intelligence assistant analyzing wearable data for a personal health tracking app.

You have been given a structured summary of a user's physiological data over the past {payload.window_days} days ({payload.date_range}).

Data summary:
- Resting heart rate mean deviation from personal baseline: {payload.rhr_mean_dev} bpm
- HRV mean deviation from personal baseline: {payload.hrv_mean_dev} ms
- Recent RHR trend (last 3 days): {payload.rhr_trend}
- Recent HRV trend (last 3 days): {payload.hrv_trend}
- Days with elevated drift score: {payload.days_flagged} out of {payload.window_days}
- Average drift score: {payload.drift_score_avg} (max possible: 2.0)

Write a short, clear health insight for this user (3-5 sentences). Cover:
1. What the data shows overall
2. Whether there is anything worth paying attention to
3. One or two concrete, actionable suggestions if warranted

Rules:
- Speak directly to the user (use "you/your")
- Be calm and informative, never alarmist
- Do not diagnose anything or name medical conditions
- Do not say "consult a doctor" unless drift_score_avg is above 1.5
- Keep it conversational, not clinical"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/insight")
async def insight(payload: InsightPayload):
    """
    Accepts a small structured summary computed client-side.
    Returns an AI-generated plain-English health insight.
    Raw health data never touches this server.
    """
    if payload.window_days < 7:
        raise HTTPException(400, "window_days must be at least 7.")
    if payload.rhr_trend not in ("up", "down", "stable"):
        raise HTTPException(400, "Invalid rhr_trend value.")
    if payload.hrv_trend not in ("up", "down", "stable"):
        raise HTTPException(400, "Invalid hrv_trend value.")

    text = generate_health_insight(payload)
    return {"insight": text}


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Static files ─────────────────────────────────────────────────────────────
_frontend = pathlib.Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
