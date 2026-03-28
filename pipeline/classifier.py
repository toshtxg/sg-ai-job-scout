import json
import logging
import os
import time

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

SYSTEM_PROMPT = (
    "You are a job market analyst specializing in AI, data, and analytics roles "
    "in Singapore. Classify job listings accurately. Always respond in valid JSON."
)

USER_PROMPT_TEMPLATE = """Classify this job listing.

Title: {title}
Company: {company}
Description (first 2000 chars): {description}

Return JSON:
{{
  "role_category": "one of: Data Scientist, ML Engineer, Data Analyst, AI Engineer, Data Engineer, Analytics Manager, MLOps Engineer, NLP Specialist, Research Scientist, BI Analyst, AI Product Manager, Other",
  "seniority_level": "one of: Junior, Mid, Senior, Lead, Principal, Director",
  "technical_skills": ["list of specific technical skills mentioned"],
  "soft_skills": ["list of soft skills mentioned"],
  "domain_knowledge": ["list of industry domains"],
  "requires_ai_ml": true or false,
  "remote_hybrid_onsite": "one of: Remote, Hybrid, Onsite, Unknown",
  "industry": "primary industry sector"
}}"""


def classify_listing(
    title: str, company: str, description: str
) -> dict | None:
    """Classify a single job listing using GPT-4o-mini."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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

        row = {
            "listing_id": listing["id"],
            "role_category": result.get("role_category", "Other"),
            "seniority_level": result.get("seniority_level", "Mid"),
            "technical_skills": result.get("technical_skills", []),
            "soft_skills": result.get("soft_skills", []),
            "domain_knowledge": result.get("domain_knowledge", []),
            "requires_ai_ml": result.get("requires_ai_ml", False),
            "remote_hybrid_onsite": result.get("remote_hybrid_onsite", "Unknown"),
            "industry": result.get("industry", "Technology"),
            "model_used": "gpt-4o-mini",
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
