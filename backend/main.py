from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import anthropic
import os
import json
import tempfile

app = FastAPI(title="HealthSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── pipeline (from your data_parse_exploration.ipynb) --

def load_data(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    records = []
    for record in root.findall('Record'):
        records.append({
            'type': record.get('type'),
            'startDate': record.get('startDate'),
            'endDate': record.get('endDate'),
            'value': record.get('value'),
        })
    df = pd.DataFrame(records)
    df['startDate'] = pd.to_datetime(df['startDate'])
    df['endDate'] = pd.to_datetime(df['endDate'])
    return df


def filter_recent_data(df, max_gap_months=1):
    df = df.sort_values('startDate').copy()
    gap_days = int(max_gap_months * 30)
    gaps = df['startDate'].diff().dt.days
    last_gap_idx = gaps[gaps > gap_days].last_valid_index()
    if last_gap_idx is None:
        return df
    pos = df.index.get_loc(last_gap_idx)
    return df.iloc[pos + 1:]


def extract_rhr(df):
    rhr = df[df['type'] == 'HKQuantityTypeIdentifierRestingHeartRate'].copy()
    rhr['value'] = pd.to_numeric(rhr['value'], errors='coerce')
    rhr['date'] = rhr['startDate'].dt.normalize().dt.date
    daily = rhr.groupby('date')['value'].mean().reset_index()
    daily.columns = ['date', 'resting_hr']
    daily['date'] = pd.to_datetime(daily['date'])
    return daily


def extract_hrv(df):
    hrv = df[df['type'] == 'HKQuantityTypeIdentifierHeartRateVariabilitySDNN'].copy()
    hrv['value'] = pd.to_numeric(hrv['value'], errors='coerce')
    hrv['date'] = hrv['startDate'].dt.normalize().dt.date
    daily = hrv.groupby('date')['value'].mean().reset_index()
    daily.columns = ['date', 'hrv']
    daily['date'] = pd.to_datetime(daily['date'])
    return daily


def compute_baselines_and_deviations(combined, baseline_window=30):
    combined = combined.copy()
    combined['rhr_baseline'] = combined['resting_hr'].rolling(window=baseline_window, min_periods=7).mean()
    combined['hrv_baseline'] = combined['hrv'].rolling(window=baseline_window, min_periods=7).mean()
    combined['rhr_dev'] = combined['resting_hr'] - combined['rhr_baseline']
    combined['hrv_dev'] = combined['hrv'] - combined['hrv_baseline']
    return combined


def drift_score(combined, rhr_threshold=5, hrv_threshold=-10):
    combined = combined.copy()
    combined['rhr_flag'] = combined['rhr_dev'] > rhr_threshold
    combined['hrv_flag'] = combined['hrv_dev'] < hrv_threshold
    combined['drift_score'] = combined[['rhr_flag', 'hrv_flag']].astype(int).sum(axis=1)
    return combined


def build_insight_payload(combined, recent_window=14):
    recent = combined.tail(recent_window).copy()
    last3_rhr = recent['rhr_dev'].iloc[-3:].mean()
    last3_hrv = recent['hrv_dev'].iloc[-3:].mean()
    return {
        "rhr_mean_dev": round(float(recent['rhr_dev'].mean()), 2),
        "hrv_mean_dev": round(float(recent['hrv_dev'].mean()), 2),
        "drift_score_avg": round(float(recent['drift_score'].mean()), 2),
        "days_flagged": int(recent['drift_score'].sum()),
        "rhr_trend": "up" if last3_rhr > 2 else ("down" if last3_rhr < -2 else "stable"),
        "hrv_trend": "down" if last3_hrv < -3 else ("up" if last3_hrv > 3 else "stable"),
        "window_days": recent_window,
        "date_range": f"{recent['date'].iloc[0].date()} to {recent['date'].iloc[-1].date()}",
    }


def generate_health_insight(payload):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️ No API key set. Add ANTHROPIC_API_KEY to your environment to enable AI insights."

    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""You are a health intelligence assistant analyzing wearable data for a personal health tracking app.

You have been given a structured summary of a user's physiological data over the past {payload['window_days']} days ({payload['date_range']}).

Data summary:
- Resting heart rate mean deviation from personal baseline: {payload['rhr_mean_dev']} bpm
- HRV mean deviation from personal baseline: {payload['hrv_mean_dev']} ms
- Recent RHR trend (last 3 days): {payload['rhr_trend']}
- Recent HRV trend (last 3 days): {payload['hrv_trend']}
- Days with elevated drift score: {payload['days_flagged']} out of {payload['window_days']}
- Average drift score: {payload['drift_score_avg']} (max possible: 2.0)

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


def combined_to_chart_data(combined):
    """Convert dataframe to JSON-serialisable chart data."""
    df = combined.copy().dropna(subset=['rhr_baseline'])
    return {
        "dates": [str(d.date()) for d in df['date']],
        "rhr": [round(float(v), 1) if not np.isnan(v) else None for v in df['resting_hr']],
        "rhr_baseline": [round(float(v), 1) if not np.isnan(v) else None for v in df['rhr_baseline']],
        "hrv": [round(float(v), 1) if not np.isnan(v) else None for v in df['hrv']],
        "hrv_baseline": [round(float(v), 1) if not np.isnan(v) else None for v in df['hrv_baseline']],
        "drift_score": [int(v) for v in df['drift_score']],
    }


# ── routes ──

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename.endswith(".xml"):
        raise HTTPException(400, "Please upload an Apple Health export.xml file.")

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        raw = load_data(tmp_path)
        raw = filter_recent_data(raw)
        daily_rhr = extract_rhr(raw)
        daily_hrv = extract_hrv(raw)

        if daily_rhr.empty:
            raise HTTPException(422, "No resting heart rate data found in this export.")
        if daily_hrv.empty:
            raise HTTPException(422, "No HRV data found. Make sure your Apple Watch has recorded HRV.")

        combined = daily_rhr.merge(daily_hrv, on='date', how='inner')
        if len(combined) < 7:
            raise HTTPException(422, f"Only {len(combined)} days of overlapping RHR+HRV data found. Need at least 7.")

        combined = compute_baselines_and_deviations(combined)
        combined = drift_score(combined)

        payload = build_insight_payload(combined)
        insight = generate_health_insight(payload)
        chart_data = combined_to_chart_data(combined)

        return {
            "insight": insight,
            "payload": payload,
            "chart": chart_data,
        }
    finally:
        os.unlink(tmp_path)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")