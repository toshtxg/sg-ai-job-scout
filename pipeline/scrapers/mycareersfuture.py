import logging
from datetime import datetime

from bs4 import BeautifulSoup

from pipeline.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

MCF_API_BASE = "https://api.mycareersfuture.gov.sg/v2/jobs"
MCF_PAGE_SIZE = 100


def _parse_iso_date(raw_date) -> str | None:
    """Parse an ISO datetime string into a YYYY-MM-DD date, or None."""
    if not raw_date:
        return None
    try:
        dt = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


class MyCareersFutureScraper(BaseScraper):
    """Scraper for MyCareersFuture.gov.sg JSON API."""

    source_name = "mycareersfuture"

    def __init__(self):
        super().__init__(delay=2.5)

    def scrape(
        self,
        search_term: str,
        max_pages: int = 5,
        known_urls: set[str] | None = None,
    ) -> list[dict]:
        known = known_urls or set()
        jobs = []
        for page in range(max_pages):
            params = {
                "search": search_term,
                "limit": MCF_PAGE_SIZE,
                "page": page,
                "sortBy": "new_posting_date",
            }
            resp = self._request_with_backoff(MCF_API_BASE, params=params)
            if resp is None:
                logger.warning(
                    f"[{self.source_name}] Failed to fetch page {page} "
                    f"for '{search_term}'"
                )
                break

            try:
                data = resp.json()
            except Exception:
                logger.error(
                    f"[{self.source_name}] Non-JSON response for "
                    f"'{search_term}' page {page}"
                )
                break

            results = data.get("results", [])
            if not results:
                break

            new_this_page = 0
            for item in results:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)
                    if job["source_url"] not in known:
                        new_this_page += 1

            # Early stop: results are newest-first (sortBy=new_posting_date), so
            # once a page contributes no unseen URLs, deeper pages are all known.
            if new_this_page == 0:
                break

            # Stop if we've fetched all available results
            total = data.get("total", 0)
            if (page + 1) * MCF_PAGE_SIZE >= total:
                break

        return jobs

    def _parse_job(self, item: dict) -> dict | None:
        """Extract fields from a single MCF API result."""
        try:
            # Title
            title = item.get("title", "").strip()
            if not title:
                return None

            # Company
            company_info = item.get("postedCompany") or {}
            company = company_info.get("name", "Unknown")

            # Description — strip HTML tags
            desc_html = item.get("description", "")
            if desc_html:
                soup = BeautifulSoup(desc_html, "html.parser")
                description = soup.get_text(separator="\n", strip=True)
            else:
                description = ""

            # Salary
            salary = item.get("salary") or {}
            salary_min = salary.get("minimum")
            salary_max = salary.get("maximum")
            if salary_min is not None:
                salary_min = float(salary_min)
            if salary_max is not None:
                salary_max = float(salary_max)

            # Posting date — try metadata.createdAt, then updatedAt
            posting_date = None
            metadata = item.get("metadata") or {}
            for date_field in ("newPostingDate", "createdAt", "updatedAt"):
                raw_date = metadata.get(date_field)
                if raw_date:
                    try:
                        dt = datetime.fromisoformat(
                            raw_date.replace("Z", "+00:00")
                        )
                        posting_date = dt.strftime("%Y-%m-%d")
                        break
                    except (ValueError, TypeError):
                        continue

            # Listing lifecycle dates — same ISO parsing as posting_date
            expiry_date = _parse_iso_date(metadata.get("expiryDate"))
            original_posting_date = _parse_iso_date(
                metadata.get("originalPostingDate")
            )

            # Job URL — build from uuid
            uuid = item.get("uuid", "")
            if not uuid:
                return None
            job_url = f"https://www.mycareersfuture.gov.sg/job/{uuid}"

            # Skills from the API
            skills = [
                s.get("skill", "")
                for s in item.get("skills") or []
                if s.get("skill")
            ]

            # Salary type for raw_data context
            salary_type = salary.get("type") or {}
            salary_period = (
                salary_type.get("salaryType", "Monthly")
                if isinstance(salary_type, dict)
                else "Monthly"
            )

            # Employment types — array of objects
            employment_types = [
                et.get("employmentType", "")
                for et in item.get("employmentTypes") or []
                if et.get("employmentType")
            ]

            # Position levels — array of objects
            position_levels = [
                pl.get("position", "")
                for pl in item.get("positionLevels") or []
                if pl.get("position")
            ]

            raw_data = {
                "skills": skills,
                "salary_period": salary_period,
                "employment_types": employment_types,
                "position_levels": position_levels,
                "categories": [
                    c.get("category", "")
                    for c in item.get("categories") or []
                ],
                "uuid": uuid,
                "min_experience": item.get("minimumYearsExperience"),
                "job_post_id": metadata.get("jobPostId"),
                "expiry_date": expiry_date,
                "original_posting_date": original_posting_date,
            }

            return self.normalize_job(
                source=self.source_name,
                source_url=job_url,
                title=title,
                company=company,
                description=description,
                salary_min=salary_min,
                salary_max=salary_max,
                posting_date=posting_date,
                raw_data=raw_data,
                expiry_date=expiry_date,
                original_posting_date=original_posting_date,
            )
        except Exception as e:
            logger.error(f"[{self.source_name}] Error parsing job: {e}")
            return None
