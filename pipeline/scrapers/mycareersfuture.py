import logging
from datetime import datetime

from bs4 import BeautifulSoup

from pipeline.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

MCF_API_BASE = "https://api.mycareersfuture.gov.sg/v2/search"
MCF_PAGE_SIZE = 100


class MyCareersFutureScraper(BaseScraper):
    """Scraper for MyCareersFuture.gov.sg JSON API."""

    source_name = "mycareersfuture"

    def __init__(self):
        super().__init__(delay=2.5)

    def scrape(self, search_term: str, max_pages: int = 5) -> list[dict]:
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
                logger.error(f"[{self.source_name}] Non-JSON response for '{search_term}' page {page}")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                job = self._parse_job(item)
                if job:
                    jobs.append(job)

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
            company_info = item.get("postedCompany", {})
            company = company_info.get("name", "Unknown")

            # Description — strip HTML tags
            desc_html = item.get("description", "")
            if desc_html:
                soup = BeautifulSoup(desc_html, "html.parser")
                description = soup.get_text(separator="\n", strip=True)
            else:
                description = ""

            # Salary
            salary = item.get("salary", {})
            salary_min = salary.get("minimum")
            salary_max = salary.get("maximum")
            # Convert to float if present
            if salary_min is not None:
                salary_min = float(salary_min)
            if salary_max is not None:
                salary_max = float(salary_max)

            # Posting date
            posting_date = None
            new_posting_date = item.get("metadata", {}).get("newPostingDate")
            if new_posting_date:
                try:
                    dt = datetime.fromisoformat(
                        new_posting_date.replace("Z", "+00:00")
                    )
                    posting_date = dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

            # Job URL
            uuid = item.get("uuid", "")
            metadata = item.get("metadata", {})
            job_url = metadata.get("jobDetailsUrl", "")
            if not job_url and uuid:
                job_url = f"https://www.mycareersfuture.gov.sg/job/{uuid}"
            if not job_url:
                return None

            # Skills from the API
            skills = [s.get("skill", "") for s in item.get("skills", []) if s.get("skill")]

            # Salary type for raw_data context
            salary_type = salary.get("type", {})
            salary_period = salary_type.get("salaryType", "Monthly") if isinstance(salary_type, dict) else "Monthly"

            raw_data = {
                "skills": skills,
                "salary_period": salary_period,
                "employment_type": item.get("employmentType", ""),
                "seniority": item.get("positionLevels", []),
                "categories": [c.get("category", "") for c in item.get("categories", [])],
                "uuid": uuid,
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
            )
        except Exception as e:
            logger.error(f"[{self.source_name}] Error parsing job: {e}")
            return None
