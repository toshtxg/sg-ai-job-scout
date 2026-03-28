import logging

from bs4 import BeautifulSoup

from pipeline.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

JOBSTREET_BASE = "https://www.jobstreet.com.sg"


class JobStreetScraper(BaseScraper):
    """Scraper for JobStreet SG. May be blocked by CloudFlare."""

    source_name = "jobstreet"

    def __init__(self):
        super().__init__(delay=3.0)
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def scrape(self, search_term: str, max_pages: int = 3) -> list[dict]:
        slug = search_term.lower().replace(" ", "-")
        jobs = []

        for page in range(1, max_pages + 1):
            url = f"{JOBSTREET_BASE}/{slug}-jobs"
            params = {"pg": page} if page > 1 else None
            resp = self._request_with_backoff(url, params=params)
            if resp is None:
                break

            if resp.status_code == 403 or "cf-browser-verification" in resp.text:
                logger.warning(
                    f"[{self.source_name}] CloudFlare blocked request. "
                    "Skipping JobStreet — would need headless browser."
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
        """Attempt to parse job listings from JobStreet HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # JobStreet uses various structures — try common selectors
        cards = soup.select(
            "article[data-testid*='job-card'], "
            "[data-search-sol-meta], "
            ".job-card"
        )
        if not cards:
            cards = soup.select("a[href*='/job/']")

        jobs = []
        for card in cards:
            try:
                title_el = card.select_one("h1, h2, h3, [data-testid*='title']")
                company_el = card.select_one(
                    "[data-testid*='company'], span[class*='company']"
                )
                salary_el = card.select_one(
                    "[data-testid*='salary'], span[class*='salary']"
                )

                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                link = card.get("href", "") or ""
                link_el = card.select_one("a[href*='/job/']")
                if not link and link_el:
                    link = link_el.get("href", "")
                if link and not link.startswith("http"):
                    link = f"{JOBSTREET_BASE}{link}"
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
