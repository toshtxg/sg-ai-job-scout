import os

from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str) -> str:
    """Retrieve secret from st.secrets (Streamlit Cloud) or os.environ (local/pipeline)."""
    try:
        import streamlit as st

        return st.secrets[key]
    except Exception:
        return os.environ.get(key, "")


SUPABASE_URL = get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("SUPABASE_KEY")
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
OPENAI_CLASSIFIER_MODEL = get_secret("OPENAI_CLASSIFIER_MODEL") or "gpt-5-nano"
OPENAI_SUMMARY_MODEL = get_secret("OPENAI_SUMMARY_MODEL") or "gpt-5-nano"

SEARCH_TERMS = [
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "AI engineer",
    "data engineer",
    "analytics",
    "MLOps",
    "NLP",
    "LLM",
]

MCF_API_BASE = "https://api.mycareersfuture.gov.sg/v2/jobs"
MCF_PAGE_SIZE = 100
MCF_DELAY_SECONDS = 2.5
MCF_USER_AGENT = "SGAIJobScout/1.0 (research project)"

ROLE_CATEGORIES = [
    "Data Scientist",
    "ML Engineer",
    "Data Analyst",
    "AI Engineer",
    "Data Engineer",
    "Analytics Manager",
    "MLOps Engineer",
    "NLP Specialist",
    "Research Scientist",
    "BI Analyst",
    "AI Product Manager",
    "Other",
]

SENIORITY_LEVELS = ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"]
