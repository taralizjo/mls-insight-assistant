# MLS Insight Assistant

A Streamlit app that gives real-estate brokers a quick read on a housing market: typical prices, price per square foot, ZIP-by-ZIP comparisons and comparable sales, plus a chat assistant powered by the Claude API.

**Key design choice:** every number is calculated in pandas first. Claude only explains numbers it has been given, so it can't invent figures. When the data can't answer a question (current inventory, days on market, a different city), the app says so plainly instead of guessing.

> Uses historical King County, WA home-sale data from May 2014 – May 2015. It is not live MLS data.

## What it does

- **Filter the market** by ZIP code, bedrooms, bathrooms, price range and waterfront.
- **Market snapshot:** typical (median) sale price, average price per sq ft, number of homes and average home age for the current filters.
- **ZIP comparison:** compares one or more ZIP codes with the wider King County market, e.g. "↑ 18% higher than county".
- **Chat assistant:**
  - *Comparable sales:* ask "Find waterfront homes sold between $800k and $1.2M in the last 6 months". If a detail is missing, it asks a follow-up question before searching.
  - *Market questions:* "Summarize this market for a broker" or "Are prices going up or down?". Answers come with a monthly price-trend chart.
  - *Grounded answers:* the app classifies each question, calculates the answer in pandas, and sends Claude only that summary, with instructions not to add facts.

## How it works

| File | Role |
| --- | --- |
| `app.py` | Page layout, filters, metrics and ZIP comparison |
| `utils/data_loader.py` | Loads and cleans the data; adds sale year/month, price per sq ft, house age and a renovation flag; removes invalid rows |
| `utils/market_assistant.py` | Chat UI; routes each message to the comparable-sales or market-analysis flow |
| `utils/comparable_sales_skill.py` | Pulls price, date and waterfront criteria out of plain English and asks for missing ones |
| `utils/market_analysis_skill.py` | Classifies market questions and calculates trends and month-over-month changes |
| `utils/ai_helper.py` | Builds a compact market summary and calls Claude with a grounding system prompt |
| `utils/listings.py`, `utils/market_comparison.py`, `utils/metrics.py`, `utils/charts.py` | Search, ZIP comparison, metrics and Plotly charts |

## Data

`data/kc_house_data.csv`: 21,613 home sales across 70 King County ZIP codes, from the public Kaggle dataset *House Sales in King County, USA*. After cleaning (removing zero prices, zero living area, 0 or more than 10 bedrooms, zero bathrooms and negative house ages), 21,583 sales remain.

## Run it locally

```bash
pip install -r requirements.txt
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml   # then add your own Anthropic API key
streamlit run app.py
```

The filters, metrics and comparable-sales search work without an API key. The written market explanations need one.

## Tech

Python · pandas · Streamlit · Plotly · Anthropic Claude API (Claude Haiku 4.5 by default)

## Limitations

- The data is historical (2014–2015) and covers one county.
- No active listings, days on market or buyer/seller counts, so the assistant declines questions that need them.
- Question routing is keyword-based, so some unusual phrasings fall back to a general market summary.

---

Built by **Tara Joseph** · [LinkedIn](https://www.linkedin.com/in/joseph-tara)
