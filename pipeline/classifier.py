import json
import logging
import os
import time

from openai import OpenAI, APIError

from pipeline.skills_normalizer import normalize_skills

logger = logging.getLogger(__name__)


def _get_required_env(name: str, default: str | None = None) -> str:
    value = (os.environ.get(name) or "").strip()
    if value:
        return value
    if default is not None:
        return default
    raise RuntimeError(f"{name} must be set")


OPENAI_API_KEY = _get_required_env("OPENAI_API_KEY")
CLASSIFIER_MODEL = _get_required_env("OPENAI_CLASSIFIER_MODEL", "gpt-5-nano")
CLASSIFICATION_BATCH_SIZE = int(
    (os.environ.get("OPENAI_CLASSIFIER_BATCH_SIZE") or "10").strip()
)
DESCRIPTION_CHAR_LIMIT = int(
    (os.environ.get("OPENAI_CLASSIFIER_DESCRIPTION_CHAR_LIMIT") or "1200").strip()
)
REQUEST_DELAY_SECONDS = float(
    (os.environ.get("OPENAI_CLASSIFIER_REQUEST_DELAY_SECONDS") or "0.2").strip()
)
client = OpenAI(api_key=OPENAI_API_KEY)
_warned_upsert_fallback = False


class ClassificationPipelineError(RuntimeError):
    """Raised when classification cannot safely continue."""

SYSTEM_PROMPT = (
    "You are a job market analyst specializing in AI, data, and analytics roles "
    "in Singapore. Classify job listings accurately. "
    "You MUST use ONLY the exact enum values provided — never invent new categories. "
    "Always respond in valid JSON."
)

CLASSIFICATION_RULES = """IMPORTANT RULES:
- role_category MUST be one of the exact values listed. Pick the BEST match.
- Use "Other" for roles that are NOT about working with data/analytics/AI/ML/BI as a core function. Examples of "Other": Data Center Engineers, Sales Engineers, Marketing roles, Software Engineers (without data/AI focus), Network Engineers, Project Managers, IT Support, Accounts/Finance roles.
- "Business Analyst" roles focused on data, reporting, or analytics should be classified as Data Analyst or BI Analyst.
- "Data Center" / "Data Centre" roles are physical infrastructure — always classify as "Other".
- Most data/analytics jobs fit into Data Analyst, BI Analyst, or Analytics Manager.
- Most AI/ML jobs fit into AI Engineer, ML Engineer, Data Scientist, or NLP Specialist.
- seniority_level: infer from title and years of experience mentioned. Default to "Mid" if unclear.
"""

SINGLE_RESULT_SCHEMA = """{
  "role_category": "MUST be exactly one of: Data Scientist | ML Engineer | Data Analyst | AI Engineer | Data Engineer | Analytics Manager | MLOps Engineer | NLP Specialist | Research Scientist | BI Analyst | AI Product Manager | Other",
  "seniority_level": "MUST be exactly one of: Junior | Mid | Senior | Lead | Principal | Director",
  "technical_skills": ["list of specific technical skills mentioned"],
  "soft_skills": ["list of soft skills mentioned"],
  "domain_knowledge": ["list of industry domains"],
  "requires_ai_ml": true or false,
  "remote_hybrid_onsite": "MUST be exactly one of: Remote | Hybrid | Onsite | Unknown",
  "industry": "primary industry sector"
}"""

USER_PROMPT_TEMPLATE = """Classify this job listing into the categories below.

Title: {title}
Company: {company}
Description (first {description_limit} chars): {description}

{classification_rules}

Return JSON:
{result_schema}"""

BATCH_USER_PROMPT_TEMPLATE = """Classify each job listing independently.

{classification_rules}

Return JSON in this exact top-level shape:
{{
  "results": [
    {{
      "index": 0,
      "role_category": "MUST be exactly one of: Data Scientist | ML Engineer | Data Analyst | AI Engineer | Data Engineer | Analytics Manager | MLOps Engineer | NLP Specialist | Research Scientist | BI Analyst | AI Product Manager | Other",
      "seniority_level": "MUST be exactly one of: Junior | Mid | Senior | Lead | Principal | Director",
      "technical_skills": ["list of specific technical skills mentioned"],
      "soft_skills": ["list of soft skills mentioned"],
      "domain_knowledge": ["list of industry domains"],
      "requires_ai_ml": true or false,
      "remote_hybrid_onsite": "MUST be exactly one of: Remote | Hybrid | Onsite | Unknown",
      "industry": "primary industry sector"
    }}
  ]
}}

You MUST return exactly one result for every input listing.
- Preserve the input order.
- Use the provided zero-based "index" for each result.
- Never omit an index and never invent extra indexes.

Listings:
{listings}"""


def _format_listing_block(index: int, listing: dict) -> str:
    return (
        f"[{index}]\n"
        f"Title: {listing['title']}\n"
        f"Company: {listing.get('company') or 'Unknown'}\n"
        f"Description (first {DESCRIPTION_CHAR_LIMIT} chars): "
        f"{(listing.get('description') or '')[:DESCRIPTION_CHAR_LIMIT]}"
    )


def _build_classification_row(listing: dict, result: dict) -> dict:
    return {
        "listing_id": listing["id"],
        "role_category": result.get("role_category", "Other"),
        "seniority_level": result.get("seniority_level", "Mid"),
        "technical_skills": normalize_skills(result.get("technical_skills", [])),
        "soft_skills": normalize_skills(result.get("soft_skills", [])),
        "domain_knowledge": result.get("domain_knowledge", []),
        "requires_ai_ml": result.get("requires_ai_ml", False),
        "remote_hybrid_onsite": result.get("remote_hybrid_onsite", "Unknown"),
        "industry": result.get("industry", "Technology"),
        "model_used": CLASSIFIER_MODEL,
    }


def _store_classification_rows(supabase_client, rows: list[dict]) -> int:
    global _warned_upsert_fallback

    if not rows:
        return 0

    try:
        response = (
            supabase_client.table("classified_listings")
            .upsert(rows, on_conflict="listing_id")
            .execute()
        )
        return len(response.data)
    except Exception as upsert_error:
        if not _warned_upsert_fallback:
            logger.warning(
                "classified_listings upsert failed. Run "
                "sql/migrations/2026-04-27-classified-listings-uniqueness.sql "
                "in Supabase, then retry. Falling back to plain insert for now: %s",
                upsert_error,
            )
            _warned_upsert_fallback = True
        else:
            logger.error("Batch upsert failed: %s", upsert_error)

    try:
        response = supabase_client.table("classified_listings").insert(rows).execute()
        return len(response.data)
    except Exception as insert_error:
        logger.error("Failed to store classification batch: %s", insert_error)
        return 0


def classify_listing(
    title: str, company: str, description: str
) -> dict | None:
    """Classify a single job listing using the configured OpenAI model."""
    try:
        response = client.chat.completions.create(
            model=CLASSIFIER_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        title=title,
                        company=company or "Unknown",
                        description=(description or "")[:DESCRIPTION_CHAR_LIMIT],
                        description_limit=DESCRIPTION_CHAR_LIMIT,
                        classification_rules=CLASSIFICATION_RULES,
                        result_schema=SINGLE_RESULT_SCHEMA,
                    ),
                },
            ],
        )
        return json.loads(response.choices[0].message.content)
    except APIError as e:
        if e.code == "insufficient_quota":
            logger.error("OpenAI quota exhausted — aborting classification.")
            raise
        logger.error(f"Classification failed for '{title}': {e}")
        return None
    except Exception as e:
        logger.error(f"Classification failed for '{title}': {e}")
        return None


def classify_batch(listings: list[dict]) -> list[dict | None]:
    """Classify a batch of listings in one OpenAI request."""
    if not listings:
        return []

    listing_blocks = "\n\n".join(
        _format_listing_block(index, listing)
        for index, listing in enumerate(listings)
    )

    try:
        response = client.chat.completions.create(
            model=CLASSIFIER_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": BATCH_USER_PROMPT_TEMPLATE.format(
                        classification_rules=CLASSIFICATION_RULES,
                        listings=listing_blocks,
                    ),
                },
            ],
        )
        payload = json.loads(response.choices[0].message.content)
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("Batch response missing results list")

        parsed_results: list[dict | None] = [None] * len(listings)
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if (
                isinstance(index, int)
                and 0 <= index < len(listings)
                and parsed_results[index] is None
            ):
                item = dict(item)
                item.pop("index", None)
                parsed_results[index] = item

        missing_indexes = [
            str(index)
            for index, result in enumerate(parsed_results)
            if result is None
        ]
        if missing_indexes:
            logger.warning(
                "Batch response missing %s result(s): %s",
                len(missing_indexes),
                ", ".join(missing_indexes),
            )

        return parsed_results
    except APIError as e:
        if e.code == "insufficient_quota":
            logger.error("OpenAI quota exhausted — aborting classification.")
            raise
        logger.error(
            "Batch classification failed for %s listing(s): %s",
            len(listings),
            e,
        )
        return [None] * len(listings)
    except Exception as e:
        logger.error(
            "Batch classification failed for %s listing(s): %s",
            len(listings),
            e,
        )
        return [None] * len(listings)


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


def classify_unprocessed(
    supabase_client, limit: int | None = None, batch_size: int | None = None
) -> int:
    """Find and classify listings not yet in classified_listings."""
    # Get already-classified listing IDs
    classified_ids = set()
    page_size = 1000
    offset = 0
    while True:
        classified_resp = (
            supabase_client.table("classified_listings")
            .select("listing_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        classified_ids.update(row["listing_id"] for row in classified_resp.data)
        if len(classified_resp.data) < page_size:
            break
        offset += page_size

    # Get all raw listings, paginating if needed
    all_raw = []
    offset = 0
    while True:
        resp = (
            supabase_client.table("raw_listings")
            .select("id, title, company, description, posting_date, scraped_at")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_raw.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size

    # Filter to unclassified
    unclassified = [r for r in all_raw if r["id"] not in classified_ids]
    unclassified.sort(
        key=lambda row: (
            row.get("posting_date") or "",
            row.get("scraped_at") or "",
            row["id"],
        ),
        reverse=True,
    )
    logger.info(f"Found {len(unclassified)} unclassified listings")
    logger.info(f"Using classifier model: {CLASSIFIER_MODEL}")

    if not unclassified:
        return 0

    if batch_size is None:
        batch_size = CLASSIFICATION_BATCH_SIZE
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive when provided")
        unclassified = unclassified[:limit]
        logger.info(
            "Processing %s listings in this run (limit=%s, batch_size=%s)",
            len(unclassified),
            limit,
            batch_size,
        )
    else:
        logger.info(
            "Processing %s listings in this run (batch_size=%s)",
            len(unclassified),
            batch_size,
        )

    count = 0
    consecutive_failures = 0
    for offset in range(0, len(unclassified), batch_size):
        batch = unclassified[offset : offset + batch_size]
        try:
            if len(batch) == 1:
                results = [
                    classify_listing(
                        batch[0]["title"],
                        batch[0].get("company"),
                        batch[0].get("description"),
                    )
                ]
            else:
                results = classify_batch(batch)
        except APIError as e:
            if e.code == "insufficient_quota":
                message = (
                    f"Quota exhausted after classifying {count} listings. "
                    f"{len(unclassified) - count} remain."
                )
                logger.error(message)
                raise ClassificationPipelineError(message) from e
            results = [None] * len(batch)

        rows_to_store = []
        for listing, result in zip(batch, results):
            if result is None:
                continue
            result = _enforce_enums(result)
            rows_to_store.append(_build_classification_row(listing, result))

        stored_count = _store_classification_rows(supabase_client, rows_to_store)
        if stored_count == 0:
            consecutive_failures += 1
            if consecutive_failures >= 5:
                message = (
                    f"5 consecutive failures — stopping. Classified {count} so far."
                )
                logger.error(message)
                raise ClassificationPipelineError(message)
            continue

        consecutive_failures = 0
        count += stored_count
        processed = offset + len(batch)
        logger.info(
            "Classification progress: processed %s/%s input listings, stored %s",
            processed,
            len(unclassified),
            count,
        )

        if REQUEST_DELAY_SECONDS > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

    return count
