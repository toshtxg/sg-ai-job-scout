import json
import logging
import os
import time

from openai import OpenAI

from pipeline.skills_normalizer import normalize_skills

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = (
    "You are a job market analyst specializing in AI, data, and analytics roles "
    "in Singapore. Classify job listings accurately. "
    "You MUST use ONLY the exact enum values provided — never invent new categories. "
    "Always respond in valid JSON."
)

USER_PROMPT_TEMPLATE = """Classify this job listing into the categories below.

Title: {title}
Company: {company}
Description (first 2000 chars): {description}

IMPORTANT RULES:
- role_category MUST be one of the exact values listed. Pick the BEST match.
- Use "Other" for roles that are NOT about working with data/analytics/AI/ML/BI as a core function. Examples of "Other": Data Center Engineers, Sales Engineers, Marketing roles, Software Engineers (without data/AI focus), Network Engineers, Project Managers, IT Support, Accounts/Finance roles.
- "Business Analyst" roles focused on data, reporting, or analytics should be classified as Data Analyst or BI Analyst.
- "Data Center" / "Data Centre" roles are physical infrastructure — always classify as "Other".
- Most data/analytics jobs fit into Data Analyst, BI Analyst, or Analytics Manager.
- Most AI/ML jobs fit into AI Engineer, ML Engineer, Data Scientist, or NLP Specialist.
- seniority_level: infer from title and years of experience mentioned. Default to "Mid" if unclear.

Return JSON:
{{
  "role_category": "MUST be exactly one of: Data Scientist | ML Engineer | Data Analyst | AI Engineer | Data Engineer | Analytics Manager | MLOps Engineer | NLP Specialist | Research Scientist | BI Analyst | AI Product Manager | Other",
  "seniority_level": "MUST be exactly one of: Junior | Mid | Senior | Lead | Principal | Director",
  "technical_skills": ["list of specific technical skills mentioned"],
  "soft_skills": ["list of soft skills mentioned"],
  "domain_knowledge": ["list of industry domains"],
  "requires_ai_ml": true or false,
  "remote_hybrid_onsite": "MUST be exactly one of: Remote | Hybrid | Onsite | Unknown",
  "industry": "primary industry sector"
}}"""


def classify_listing(
    title: str, company: str, description: str
) -> dict | None:
    """Classify a single job listing using GPT-5.4-mini."""
    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        title=title,
                        company=company or "Unknown",
                        description=(description or "")[:2000],
                    ),
                },
            ],
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Classification failed for '{title}': {e}")
        return None


VALID_ROLES = {
    "Data Scientist", "ML Engineer", "Data Analyst", "AI Engineer",
    "Data Engineer", "Analytics Manager", "MLOps Engineer", "NLP Specialist",
    "Research Scientist", "BI Analyst", "AI Product Manager", "Other",
}
VALID_SENIORITY = {"Junior", "Mid", "Senior", "Lead", "Principal", "Director"}
VALID_WORK_MODE = {"Remote", "Hybrid", "Onsite", "Unknown"}


def _enforce_enums(result: dict) -> dict:
    """Force classification values into valid enum sets."""
    if result.get("role_category") not in VALID_ROLES:
        result["role_category"] = "Other"
    if result.get("seniority_level") not in VALID_SENIORITY:
        result["seniority_level"] = "Mid"
    if result.get("remote_hybrid_onsite") not in VALID_WORK_MODE:
        result["remote_hybrid_onsite"] = "Unknown"
    return result


def classify_unprocessed(supabase_client) -> int:
    """Find and classify listings not yet in classified_listings."""
    # Get already-classified listing IDs
    classified_resp = (
        supabase_client.table("classified_listings")
        .select("listing_id")
        .execute()
    )
    classified_ids = {row["listing_id"] for row in classified_resp.data}

    # Get all raw listings, paginating if needed
    all_raw = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase_client.table("raw_listings")
            .select("id, title, company, description")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_raw.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    # Filter to unclassified
    unclassified = [r for r in all_raw if r["id"] not in classified_ids]
    logger.info(f"Found {len(unclassified)} unclassified listings")

    count = 0
    for listing in unclassified:
        result = classify_listing(
            listing["title"],
            listing.get("company"),
            listing.get("description"),
        )
        if result is None:
            continue

        result = _enforce_enums(result)

        row = {
            "listing_id": listing["id"],
            "role_category": result.get("role_category", "Other"),
            "seniority_level": result.get("seniority_level", "Mid"),
            "technical_skills": normalize_skills(result.get("technical_skills", [])),
            "soft_skills": normalize_skills(result.get("soft_skills", [])),
            "domain_knowledge": result.get("domain_knowledge", []),
            "requires_ai_ml": result.get("requires_ai_ml", False),
            "remote_hybrid_onsite": result.get("remote_hybrid_onsite", "Unknown"),
            "industry": result.get("industry", "Technology"),
            "model_used": "gpt-5.4-mini",
        }

        try:
            supabase_client.table("classified_listings").insert(row).execute()
            count += 1
        except Exception as e:
            logger.error(
                f"Failed to store classification for listing {listing['id']}: {e}"
            )

        # Small delay to avoid rate limits
        time.sleep(0.2)

    return count
