# SG AI Job Market Scout

A Streamlit dashboard that tracks and analyzes Singapore's AI, data science, and analytics job market. Job listings are sourced from [MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/), classified using GPT-5-nano by default, and presented through interactive visualizations.

**Live app:** [sg-ai-job-scout.streamlit.app](https://sg-ai-job-scout.streamlit.app/)

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Architecture

```
sg-ai-job-scout/
├── app/                          # Streamlit frontend
│   ├── Home.py                   # Main entry point
│   ├── pages/                    # Multi-page app
│   │   ├── 1_Dashboard.py        # Overview metrics, new listings, charts
│   │   ├── 2_Job_Explorer.py     # Filterable job browser with apply links
│   │   ├── 3_Role_Taxonomy.py    # Skills heatmap & role analysis
│   │   ├── 5_Company_Leaderboard.py  # Top hiring companies & profiles
│   │   ├── 6_Jobs_For_You.py     # Personalised job matching
│   │   ├── 8_AI_Skills_Deep_Dive.py  # 11-category AI skills taxonomy
│   │   ├── 10_Learning_Roadmap.py    # Skill progression & learning paths
│   │   └── 11_Market_Pulse.py    # Market landscape & industry adoption
│   ├── pages_hidden/             # Preserved but hidden from nav
│   │   ├── 7_Skills_Gap.py
│   │   └── 9_Skills_Salary_Premium.py
│   ├── components/               # Reusable UI components
│   │   ├── charts.py             # Plotly chart builders
│   │   ├── filters.py            # Role scope toggle & job filters
│   │   └── metrics.py            # Metric card row
│   └── utils/                    # Config & Supabase client
├── pipeline/                     # Data pipeline
│   ├── scrapers/
│   │   ├── base_scraper.py       # Abstract base with backoff
│   │   └── mycareersfuture.py    # MCF API scraper (59 search terms)
│   ├── classifier.py             # GPT-5-nano structured classification
│   ├── ai_skills_analyzer.py     # 281-keyword AI skills taxonomy
│   ├── skills_normalizer.py      # Canonical skill name mapping
│   ├── snapshot.py               # Market snapshot aggregation
│   ├── reclassify_others.py      # Re-classification utility
│   └── run_pipeline.py           # Pipeline orchestrator
├── sql/schema.sql                # Database DDL (run in Supabase)
├── .github/workflows/scrape.yml  # Automated scraping (daily at 2am UTC)
├── pyproject.toml
├── requirements.txt
└── .env.example
```

**Data flow:** MyCareersFuture API → Supabase (raw_listings) → GPT-5-nano classifier → Supabase (classified_listings) → Snapshot aggregation → Streamlit dashboard

## Pages

| Page | What it does |
|------|-------------|
| **Dashboard** | Market metrics, role & salary charts, "New This Week" table with apply links, work mode summary, AI-generated market briefing |
| **Job Explorer** | Browse all jobs with filters (role, seniority, salary, skills, AI involvement). Each listing shows salary, work mode icon, skills tags, and direct apply link |
| **Jobs for You** | Enter your skills → see matching jobs ranked by skill overlap, with green/red skill highlighting and apply links. Includes "Skills to Learn Next" recommendations |
| **Roles & Skills** | Top skills bar chart, skills-by-role heatmap |
| **Company Leaderboard** | Top hiring companies, company deep-dives with role breakdown, salary distribution, and open roles table |
| **AI Skills Deep Dive** | 11-category AI taxonomy (Prompt Engineering → Responsible AI), tier breakdown, keyword analysis, AI skills by role heatmap |
| **Learning Roadmap** | Skill progression heatmap by seniority, role-based learning paths with Foundation/Differentiator/Specialist tiers |
| **Market Pulse** | AI salary premium, top 20 skills by demand, industry AI adoption |

## Key Features

- **Role scope filter** — defaults to Data & Analytics roles (Data Scientist, Data Analyst, Data Engineer, BI Analyst, Analytics Manager). Switch to All Roles or customize.
- **AI involvement filter** — 4 levels: Uses AI to augment, Uses ML models, AI/LLM Engineering, MLOps & Infrastructure
- **Direct apply links** — every listing links to the original MyCareersFuture posting
- **Work mode indicators** — 🏠 Remote, 🔄 Hybrid, 🏢 Onsite
- **281-keyword AI taxonomy** — 11 categories across 3 career tiers, sourced from Stanford AI Index 2025, PwC, Lightcast
- **Skill matching** — 50%+ skill overlap = strong match in Jobs for You

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit, Plotly |
| Database | Supabase (PostgreSQL) |
| AI Classification | OpenAI GPT-5-nano (JSON mode, configurable) |
| Data Source | MyCareersFuture.gov.sg (JSON API) |
| Automation | GitHub Actions (cron: daily at 2am UTC) |
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

Scrapes jobs, classifies with GPT-5-nano by default, generates a market snapshot. Subsequent runs only process new/unclassified listings.

### 5. Launch the dashboard

```bash
streamlit run app/Home.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Set **Main file path** to `app/Home.py`
4. Add secrets in app settings:
   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   OPENAI_API_KEY = "sk-your-key"
   ```

## GitHub Actions (Automated Scraping)

The pipeline runs automatically every day at 2 AM UTC.

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add repository secrets: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
3. Optional overrides: `OPENAI_CLASSIFIER_MODEL`, `OPENAI_SUMMARY_MODEL`

You can also trigger manually from Actions → Scrape & Classify → Run workflow.

## Data Source

- **[MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/)** — Singapore government job portal (JSON API)
- 59 search terms covering AI, data science, analytics, ML, NLP, BI, and related fields
- ~2,100 listings classified across 11 role categories

## Disclaimer

This project is for educational and research purposes. Job listing data is sourced from the MyCareersFuture.gov.sg public API. AI classification is approximate and may not perfectly categorize every listing. Salary data reflects what is posted and may not represent actual compensation.

## License

MIT
