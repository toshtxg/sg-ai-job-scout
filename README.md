# SG AI Job Market Scout

A Streamlit dashboard that tracks and analyzes Singapore's AI, data science, and analytics job market. Job listings are sourced from [MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/), classified using GPT-5.4-mini, and presented through interactive visualizations.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Architecture

```
sg-ai-job-scout/
├── app/                          # Streamlit frontend
│   ├── Home.py                   # Main entry point
│   ├── pages/                    # Multi-page app
│   │   ├── 1_Dashboard.py        # Overview metrics & charts
│   │   ├── 2_Job_Explorer.py     # Filterable job browser (CSV export)
│   │   ├── 3_Role_Taxonomy.py    # Skills & role analysis
│   │   ├── 4_Trends.py           # Time-series trends
│   │   ├── 5_Company_Leaderboard.py
│   │   ├── 6_Salary_Estimator.py
│   │   ├── 7_Skills_Gap.py       # Skills gap analyzer
│   │   └── 8_AI_Skills_Deep_Dive.py  # AI skills taxonomy
│   ├── components/               # Reusable UI components
│   └── utils/                    # Config & Supabase client
├── pipeline/                     # Data pipeline
│   ├── scrapers/                 # Job site scrapers
│   │   ├── base_scraper.py       # Abstract base with backoff
│   │   └── mycareersfuture.py    # MCF API scraper
│   ├── classifier.py             # GPT-5.4-mini classification
│   ├── ai_skills_analyzer.py     # 281-keyword AI skills taxonomy
│   ├── skills_normalizer.py      # Canonical skill name mapping
│   ├── snapshot.py               # Market snapshot aggregation
│   └── run_pipeline.py           # Pipeline orchestrator
├── sql/                          # Database schema
│   └── schema.sql                # Run in Supabase Dashboard
├── .github/workflows/scrape.yml  # Automated scraping (Mon & Thu)
├── pyproject.toml                # Python package config
├── requirements.txt
└── .env.example
```

**Data flow:** MyCareersFuture API → Supabase (raw_listings) → GPT-5.4-mini classifier → Supabase (classified_listings) → Snapshot aggregation → Streamlit dashboard

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit, Plotly |
| Database | Supabase (PostgreSQL) |
| AI Classification | OpenAI GPT-5.4-mini |
| AI Skills Analysis | 281-keyword taxonomy across 11 categories |
| Data Source | MyCareersFuture.gov.sg (JSON API) |
| Automation | GitHub Actions (cron) |
| Language | Python 3.11+ |

## Setup

### 1. Clone & install

```bash
git clone https://github.com/toshtxg/sg-ai-job-scout.git
cd sg-ai-job-scout
python3 -m venv venv
source venv/bin/activate
pip install -e .
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
python -m pipeline.run_pipeline
```

This scrapes jobs from the MyCareersFuture.gov.sg API, classifies them with GPT-5.4-mini, and generates a market snapshot. Subsequent runs only scrape new listings and classify unprocessed ones.

### 5. Launch the dashboard

```bash
streamlit run app/Home.py
```

## Pages

| Page | Description |
|------|-------------|
| Dashboard | Metrics, role distribution, salary comparison, AI market summary |
| Job Explorer | Filterable job browser with CSV export |
| Role Taxonomy | Sunburst chart, skills heatmap, co-occurrence analysis |
| Trends | Time-series trends (grows with each pipeline run) |
| Company Leaderboard | Top hiring companies, company profiles |
| Salary Estimator | Estimate salary by role + seniority + skills |
| Skills Gap | Input your skills, see which roles match and what to learn |
| AI Skills Deep Dive | 11-category AI skills taxonomy — surface vs deep AI demand |
| Skills Salary Premium | Which skills pay more? Premium analysis by skill and role |
| Learning Roadmap | Skill progression by seniority, co-occurrence paths, role-based learning |
| Market Pulse | AI vs non-AI market comparison, skill rarity index, industry adoption |

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Set **Main file path** to `app/Home.py`
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

## Data Source

- **[MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/)** — Singapore government job portal (JSON API)

## Disclaimer

This project is for educational and research purposes. Job listing data is sourced from the MyCareersFuture.gov.sg public API. The AI classification is approximate and may not perfectly categorize every listing. Salary data reflects what is posted and may not represent actual compensation.

## License

MIT
