## HealthSync -- Longitudinal Heart Health Intelligence Engine

### Overview (updated: 2/17/26)
HealthSync is a patient-first health intelligence system designed to detect meaningful changes in cardiovascular-related metrics over time.

The system focuses on longitudinal trend detection rather than diagnosis. It analyzes wearable data (e.g., resting heart rate, sleep, activity) to:

- Establish a personal baseline
- Detect sustained deviations from that baseline
- Identify potential associations between behavior and physiological response
- Generate structured weekly summaries

This system does not diagnose, predict medical events, or replace professional medical care. It is designed to support self-awareness and more informed clinical conversations.

### Problem
Many individuals monitor wearable health data daily but lack:

- Context for what is “normal” for them
- Visibility into gradual trend changes
- Understanding of how habits influence physiological metrics
- Clear summaries to bring to healthcare providers

Healthcare interactions are episodic. Wearable data is continuous. There is a gap between raw data and actionable understanding.

### Scope (Phase 1)
Initial focus: Early heart health monitoring.

Target user: 
- Individuals in their 20s-40s
- Generally healthy but health-conscious
- May have family history or borderline cardiovascular indicators
- Use wearable devices regularly

Supported inputs: 
- Supported inputs (v1):
- Resting heart rate
- ~~Sleep metrics~~
- Activity metrics

#### What This System Does
- Computes rolling personal baselines
- Detects sustained upward or downward drift
- Quantifies deviation from baseline
- Identifies simple correlations between behavior and physiological changes
- Outputs structured, safe insight objects

#### What This System Does NOT Do
- Diagnose medical conditions
- Predict heart attacks or disease
- Provide medical treatment advice
- Replace healthcare professionals
- Interpret medical imaging or complex clinical records (v1)

### Architecture (Early Stage)
Data --> Cleaning --> Baseline Modeling --> Trend Detection --> Structured Insight --> (Future) Narrative Layer

The LLM layer, when introduced, will operate only on structured insights (not raw health data) to maintain safety and guardrails.

## Current Milestone
Phase 1 (2/17/26 - X/XX/XX): Build baseline modeling and trend detection over 8+ weeks of wearable data.