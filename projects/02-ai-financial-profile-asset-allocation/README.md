# AI-Powered Financial Profile & Asset Allocation Tool

An interactive Streamlit dashboard that uses the **Grok API (xAI)** to generate a personalised asset allocation across Equity, Debt, Gold, and Alternatives — based on a user's financial profile and risk appetite.

Built as part of the Finance + GenAI portfolio by **Veer Pratap Singh**.

---

## What It Does

1. **Risk profiling** — 5 questions scored into a 0–100 risk score and mapped to Conservative / Moderate Conservative / Moderate Aggressive / Aggressive.
2. **AI allocation** — Grok analyses the profile and returns a structured JSON allocation with per-asset-class reasoning.
3. **Fund recommendations** — Pulls top-ranked equity funds from the [Mutual Fund Analytics project](../01-mutual-fund-analytics-automation/) to suggest specific categories.
4. **Demo mode** — Works without an API key, so any portfolio visitor sees a live product.

---

## Tech Stack

- Python · Streamlit · Plotly
- Grok API via `openai` client (OpenAI-compatible endpoint)
- pandas (reads Project 1's scored fund data)
- python-dotenv

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a Grok API key (free)
- Go to [console.x.ai](https://console.x.ai)
- Sign in → API Keys → Create key

### 3. Add your key
```bash
cp .env.example .env
# Edit .env and paste your key
```

### 4. Run the app
```bash
streamlit run dashboard/app.py
```

---

## Project Structure

```
02-ai-financial-profile-asset-allocation/
├── dashboard/
│   └── app.py              # Streamlit UI
├── src/
│   ├── risk_profiler.py    # Questionnaire → risk score
│   ├── prompts.py          # Grok system prompt + user message builder
│   ├── allocation_engine.py # API call + demo fallback
│   └── fund_recommender.py # Links to Project 1 fund rankings
├── .env.example
├── requirements.txt
└── README.md
```

---

## How the Grok Integration Works

The key concept is **structured output** — rather than asking Grok for a paragraph of text, we instruct it (via `response_format={"type": "json_object"}`) to return a fixed JSON schema:

```python
from openai import OpenAI

client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
response = client.chat.completions.create(
    model="grok-3-mini",
    messages=[system_prompt, user_message],
    response_format={"type": "json_object"},
)
allocation = json.loads(response.choices[0].message.content)
```

This pattern — LLM as a **structured reasoning engine**, not a text generator — is how real GenAI products are built in production.

---

## Streamlit Cloud Deployment

Add `XAI_API_KEY` to your app's secrets in the Streamlit Cloud dashboard. The app reads it via `st.secrets["XAI_API_KEY"]` automatically.

---

## Disclaimer

For educational and portfolio demonstration purposes only. Does not constitute financial advice. Consult a SEBI-registered investment advisor before making investment decisions.
