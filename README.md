# SG AI Job Market Scout

A Streamlit dashboard that tracks and analyzes Singapore's AI, data science, and analytics job market. Job listings are scraped from MyCareersFuture.gov.sg, classified using GPT-4o-mini, and presented through interactive visualizations.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Architecture

```
sg-ai-job-scout/
├── app/                          # Streamlit frontend
│   ├── app.py                    # Main entry point
│   ├── pages/                    # Multi-page app
│   │   ├── 1_Dashboard.py        # Overview metrics & charts
│   │   ├── 2_Job_Explorer.py     # Filterable job browser
│   │   ├── 3_Role_Taxonomy.py    # Skills & role analysis
│   │   └── 4_Trends.py           # Time-series trends
│   ├── components/               # Reusable UI components
│   └── utils/                    # Config & Supabase client
├── pipeline/                     # Data pipeline
│   ├── scrapers/                 # Job site scrapers
│   ├── classifier.py             # GPT-4o-mini classification
│   ├── snapshot.py               # Market snapshot aggregation
│   └── run_pipeline.py           # Pipeline orchestrator
├── sql/                          # Database schema
├── .github/workflows/            # Automated scraping schedule
└── requirements.txt
```

**Data flow:** Scrapers → Supabase (raw_listings) → GPT-4o-mini classifier → Supabase (classified_listings) → Snapshot aggregation → Streamlit dashboard

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit, Plotly |
| Database | Supabase (PostgreSQL) |
| AI Classification | OpenAI GPT-4o-mini |
| Scraping | Requests, BeautifulSoup4 |
| Automation | GitHub Actions (cron) |
| Language | Python 3.11+ |

## Setup

### 1. Clone & install

```bash
git clone https://github.com/toshtxg/sg-ai-job-scout.git
cd sg-ai-job-scout
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create Supabase tables

Go to your [Supabase Dashboard](https://supabase.com/dashboard) → SQL Editor → paste the contents of `sql/schema.sql` and run.

### 3. Set environment variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export OPENAI_API_KEY="sk-your-key"
```

Or create a `.env` file (see `.env.example`).

### 4. Run the pipeline

```bash
python pipeline/run_pipeline.py
```

This scrapes jobs, classifies them with GPT-4o-mini, and generates a market snapshot.

### 5. Launch the dashboard

```bash
streamlit run app/app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Set **Main file path** to `app/app.py`
4. Add secrets in the app settings:
   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```
   (OPENAI_API_KEY is only needed for the pipeline, not the dashboard)

## GitHub Actions (Automated Scraping)

The pipeline runs automatically on Monday and Thursday at 2 AM UTC. To enable:

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add these repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENAI_API_KEY`

You can also trigger a manual run from Actions → Scrape & Classify → Run workflow.

## Data Sources

- **MyCareersFuture.gov.sg** — Singapore government job portal (primary source)
- **NodeFlair** — Tech job platform (CloudFlare-protected, stub scraper)
- **JobStreet SG** — Regional job platform (CloudFlare-protected, stub scraper)

## Disclaimer

This project is for educational and research purposes. Job listing data is sourced from public job portals. The AI classification is approximate and may not perfectly categorize every listing. Salary data reflects what is posted and may not represent actual compensation.

## License

MIT
