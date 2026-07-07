"""Unit checks for refresh optimizations (pure functions + stubbed scraper).

Run with: python -m pytest tests/  (or: python tests/test_pipeline_refresh.py)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# classifier.py reads OPENAI_API_KEY at import time (imported via run_pipeline)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from pipeline.scrapers.mycareersfuture import MyCareersFutureScraper, _parse_iso_date
from pipeline.snapshot import _percentile


def _mcf_item(uuid: str, **metadata) -> dict:
    """Build a minimal MCF API result item."""
    base_metadata = {"newPostingDate": "2026-07-01"}
    base_metadata.update(metadata)
    return {
        "uuid": uuid,
        "title": f"Data Engineer {uuid}",
        "postedCompany": {"name": "Acme"},
        "description": "<p>Build pipelines</p>",
        "salary": {"minimum": 5000, "maximum": 8000},
        "metadata": base_metadata,
    }


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_parse_iso_date():
    assert _parse_iso_date("2026-07-05") == "2026-07-05"
    assert _parse_iso_date("2026-07-05T10:30:00Z") == "2026-07-05"
    assert _parse_iso_date("2026-07-05T10:30:00+08:00") == "2026-07-05"
    assert _parse_iso_date(None) is None
    assert _parse_iso_date("") is None
    assert _parse_iso_date("not-a-date") is None


def test_parse_job_lifecycle_fields():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(
        _mcf_item(
            "abc123",
            expiryDate="2026-08-01",
            originalPostingDate="2026-06-15T00:00:00Z",
        )
    )
    assert job is not None
    assert job["expiry_date"] == "2026-08-01"
    assert job["original_posting_date"] == "2026-06-15"
    assert job["raw_data"]["expiry_date"] == "2026-08-01"
    assert job["raw_data"]["original_posting_date"] == "2026-06-15"
    # Missing lifecycle metadata stays None
    job2 = scraper._parse_job(_mcf_item("def456"))
    assert job2["expiry_date"] is None
    assert job2["original_posting_date"] is None


def test_scrape_early_stop():
    """Pagination stops once a page contributes zero unseen URLs."""
    scraper = MyCareersFutureScraper()
    scraper.delay = 0

    pages = {
        0: {"results": [_mcf_item("new1"), _mcf_item("known1")], "total": 400},
        1: {"results": [_mcf_item("known2"), _mcf_item("known3")], "total": 400},
        2: {"results": [_mcf_item("new2")], "total": 400},
    }
    requested = []

    def fake_request(url, params=None, max_retries=3):
        requested.append(params["page"])
        return _FakeResponse(pages[params["page"]])

    scraper._request_with_backoff = fake_request
    known = {
        f"https://www.mycareersfuture.gov.sg/job/{u}"
        for u in ("known1", "known2", "known3")
    }

    jobs = scraper.scrape("data engineer", max_pages=5, known_urls=known)
    # Page 1 has zero new URLs -> stop; page 2 is never fetched
    assert requested == [0, 1]
    urls = [j["source_url"] for j in jobs]
    # Jobs parsed before the stop are still returned (including known ones,
    # which store_listings uses for the refresh path)
    assert "https://www.mycareersfuture.gov.sg/job/new1" in urls
    assert "https://www.mycareersfuture.gov.sg/job/new2" not in urls
    assert len(jobs) == 4


def test_scrape_no_early_stop_without_known_urls():
    """Without known_urls every page counts as new — total bound still applies."""
    scraper = MyCareersFutureScraper()
    scraper.delay = 0
    pages = {
        0: {"results": [_mcf_item("a")], "total": 150},
        1: {"results": [_mcf_item("b")], "total": 150},
    }
    requested = []

    def fake_request(url, params=None, max_retries=3):
        requested.append(params["page"])
        return _FakeResponse(pages[params["page"]])

    scraper._request_with_backoff = fake_request
    jobs = scraper.scrape("data engineer", max_pages=5)
    assert requested == [0, 1]
    assert len(jobs) == 2


def test_percentile():
    assert _percentile([100.0], 0.5) == 100.0
    assert _percentile([1.0, 2.0, 3.0], 0.5) == 2.0
    assert _percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert _percentile([1.0, 2.0, 3.0, 4.0], 0.25) == 1.75
    assert _percentile([1.0, 2.0, 3.0, 4.0], 0.75) == 3.25
    assert _percentile([1.0, 2.0, 3.0], 0.0) == 1.0
    assert _percentile([1.0, 2.0, 3.0], 1.0) == 3.0


def test_store_listings_split():
    """store_listings inserts new rows fully and upserts slim refresh rows."""
    os.environ.setdefault("SUPABASE_URL", "https://x.supabase.co")
    from pipeline import run_pipeline

    calls = []

    class FakeQuery:
        def __init__(self, rows):
            self.rows = rows

        def upsert(self, rows, on_conflict=None):
            calls.append((rows, on_conflict))
            return self

        def execute(self):
            class R:
                data = calls[-1][0]

            return R()

    class FakeClient:
        def table(self, name):
            assert name == "raw_listings"
            return FakeQuery(None)

    listings = [
        {
            "source": "mycareersfuture",
            "source_url": "https://x/job/new",
            "title": "New Job",
            "company": "A",
            "description": "d",
            "salary_min": 1.0,
            "salary_max": 2.0,
            "salary_currency": "SGD",
            "posting_date": "2026-07-01",
            "expiry_date": "2026-08-01",
            "original_posting_date": "2026-06-01",
            "raw_data": {},
        },
        {
            "source": "mycareersfuture",
            "source_url": "https://x/job/known",
            "title": "Known Job",
            "company": "B",
            "description": "d",
            "salary_min": 3.0,
            "salary_max": 4.0,
            "salary_currency": "SGD",
            "posting_date": "2026-07-02",
            "expiry_date": "2026-08-02",
            "original_posting_date": "2026-06-02",
            "raw_data": {},
        },
    ]
    inserted, refreshed = run_pipeline.store_listings(
        listings, FakeClient(), {"https://x/job/known"}
    )
    assert inserted == 1
    assert refreshed == 1
    assert len(calls) == 2
    insert_rows, insert_conflict = calls[0]
    refresh_rows, refresh_conflict = calls[1]
    assert insert_conflict == "source_url"
    assert refresh_conflict == "source_url"
    assert insert_rows[0]["source_url"] == "https://x/job/new"
    assert "description" in insert_rows[0]
    # Refresh payload is slim: no description/raw_data, has lifecycle fields
    refresh = refresh_rows[0]
    assert refresh["source_url"] == "https://x/job/known"
    assert "description" not in refresh
    assert "raw_data" not in refresh
    assert refresh["expiry_date"] == "2026-08-02"
    assert refresh["original_posting_date"] == "2026-06-02"
    assert refresh["posting_date"] == "2026-07-02"
    assert refresh["salary_min"] == 3.0
    assert refresh["salary_max"] == 4.0
    assert refresh["last_seen_at"]


def test_upsert_lifecycle_fallback():
    """Unknown-column upsert failure warns and retries with lifecycle keys stripped."""
    from pipeline import run_pipeline

    run_pipeline._warned_lifecycle_upsert = False
    calls = []

    class FakeQuery:
        def upsert(self, rows, on_conflict=None):
            calls.append(rows)
            self.rows = rows
            return self

        def execute(self):
            if len(calls) == 1:
                raise Exception(
                    "column raw_listings.last_seen_at does not exist"
                )

            class R:
                data = calls[-1]

            return R()

    class FakeClient:
        def table(self, name):
            return FakeQuery()

    rows = [
        {
            "source_url": "https://x/job/known",
            "source": "mycareersfuture",
            "title": "Known Job",
            "last_seen_at": "2026-07-05T00:00:00+00:00",
            "expiry_date": "2026-08-02",
            "original_posting_date": "2026-06-02",
            "posting_date": "2026-07-02",
            "salary_min": 3.0,
            "salary_max": 4.0,
        }
    ]
    stored = run_pipeline._upsert_raw_listings(FakeClient(), rows)
    assert stored == 1
    assert len(calls) == 2
    retried = calls[1][0]
    assert "last_seen_at" not in retried
    assert "expiry_date" not in retried
    assert "original_posting_date" not in retried
    assert retried["posting_date"] == "2026-07-02"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"{name}: OK")
    print("All tests passed")
