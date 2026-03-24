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

class InsightPayload(BaseModel):
    rhr_mean_dev: float
    hrv_mean_dev: float
    drift_score_avg: float
    days_flagged: int
    rhr_trend: str
    hrv_trend: str
    window_days: int
    date_range: str

@app.post("/insight")
def insight(payload: InsightPayload):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(500, "No API key configured.")
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are a health intelligence assistant analyzing wearable data for a personal health tracking app.

Data summary ({payload.window_days} days, {payload.date_range}):
- Resting heart rate deviation from baseline: {payload.rhr_mean_dev} bpm
- HRV deviation from baseline: {payload.hrv_mean_dev} ms
- RHR trend (last 3 days): {payload.rhr_trend}
- HRV trend (last 3 days): {payload.hrv_trend}
- Days flagged: {payload.days_flagged} of {payload.window_days}
- Avg drift score: {payload.drift_score_avg} (max 2.0)

Write 3-5 sentences: what the data shows, anything worth noting, one actionable suggestion.
Speak directly to the user. Calm, not alarmist. No diagnoses. No medical conditions named.
Only suggest seeing a doctor if drift_score_avg > 1.5."""

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"insight": msg.content[0].text}

@app.get("/health")
def health():
    return {"status": "ok"}

_frontend = pathlib.Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")