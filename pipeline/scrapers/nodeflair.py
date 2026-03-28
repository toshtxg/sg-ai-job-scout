import logging

from bs4 import BeautifulSoup

from pipeline.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

NODEFLAIR_BASE = "https://nodeflair.com/jobs"


class NodeFlairScraper(BaseScraper):
    """Scraper for NodeFlair.com jobs. May be blocked by CloudFlare."""

    source_name = "nodeflair"

    def __init__(self):
        super().__init__(delay=3.0)
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def scrape(self, search_term: str, max_pages: int = 3) -> list[dict]:
        jobs = []
        for page in range(1, max_pages + 1):
            params = {"query": search_term, "page": page}
            resp = self._request_with_backoff(NODEFLAIR_BASE, params=params)
            if resp is None:
                break

            # Check for CloudFlare block
            if resp.status_code == 403 or "cf-browser-verification" in resp.text:
                logger.warning(
                    f"[{self.source_name}] CloudFlare blocked request. "
                    "Skipping NodeFlair — would need headless browser."
                )
                return []

            try:
                page_jobs = self._parse_html(resp.text)
                if not page_jobs:
                    break
                jobs.extend(page_jobs)
            except Exception as e:
                logger.error(f"[{self.source_name}] Parse error: {e}")
                break

        return jobs

    def _parse_html(self, html: str) -> list[dict]:
        """Attempt to parse job listings from NodeFlair HTML."""
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("[class*='jobCard'], [class*='job-card'], .job-listing")
        if not cards:
            # Try alternative selectors
            cards = soup.select("a[href*='/jobs/']")

        jobs = []
        for card in cards:
            try:
                title_el = card.select_one("h2, h3, [class*='title']")
                company_el = card.select_one("[class*='company']")
                salary_el = card.select_one("[class*='salary']")

                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                link = card.get("href", "") or ""
                if link and not link.startswith("http"):
                    link = f"https://nodeflair.com{link}"
                if not link:
                    continue

                company = company_el.get_text(strip=True) if company_el else None
                salary_text = salary_el.get_text(strip=True) if salary_el else ""

                salary_min, salary_max = self._parse_salary(salary_text)

                jobs.append(
                    self.normalize_job(
                        source=self.source_name,
                        source_url=link,
                        title=title,
                        company=company,
                        description="",
                        salary_min=salary_min,
                        salary_max=salary_max,
                        posting_date=None,
                    )
                )
            except Exception as e:
                logger.debug(f"[{self.source_name}] Skipping card: {e}")
                continue

        return jobs

    @staticmethod
    def _parse_salary(text: str) -> tuple[float | None, float | None]:
        """Try to extract salary range from text like '$5,000 - $8,000'."""
        import re

        numbers = re.findall(r"[\d,]+", text.replace("$", ""))
        if len(numbers) >= 2:
            try:
                return float(numbers[0].replace(",", "")), float(
                    numbers[1].replace(",", "")
                )
            except ValueError:
                pass
        return None, None
