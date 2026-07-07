"""Tests for MyCareersFutureScraper._parse_job payload extraction.

No network is used: a representative MCF API result dict is parsed directly
through the pure _parse_job method.
"""

from pipeline.scrapers.mycareersfuture import MyCareersFutureScraper


def _sample_item(**overrides):
    """A representative single MCF /v2/jobs result payload."""
    item = {
        "uuid": "abc-123",
        "title": "  Senior Data Scientist  ",
        "postedCompany": {"name": "Acme Analytics"},
        "description": "<p>Build <b>models</b>.</p><p>Own the pipeline.</p>",
        "salary": {
            "minimum": 8000,
            "maximum": 12000,
            "type": {"salaryType": "Monthly"},
        },
        "metadata": {
            "newPostingDate": "2026-06-01T00:00:00.000Z",
            "jobPostId": "JOB-999",
        },
        "skills": [
            {"skill": "Python"},
            {"skill": "SQL"},
            {"skill": ""},  # blank skill should be dropped
        ],
        "employmentTypes": [{"employmentType": "Full Time"}],
        "positionLevels": [{"position": "Senior Executive"}],
        "categories": [{"category": "Information Technology"}],
        "minimumYearsExperience": 5,
    }
    item.update(overrides)
    return item


def test_parse_job_extracts_core_fields():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item())

    assert job is not None
    assert job["source"] == "mycareersfuture"
    assert job["title"] == "Senior Data Scientist"  # stripped
    assert job["company"] == "Acme Analytics"
    assert job["source_url"] == "https://www.mycareersfuture.gov.sg/job/abc-123"
    assert job["salary_currency"] == "SGD"


def test_parse_job_strips_html_from_description():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item())
    # Tags removed; text preserved, blocks separated by newlines.
    assert "<" not in job["description"]
    assert "Build" in job["description"]
    assert "models" in job["description"]
    assert "Own the pipeline." in job["description"]


def test_parse_job_converts_salary_to_float():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item())
    assert job["salary_min"] == 8000.0
    assert isinstance(job["salary_min"], float)
    assert job["salary_max"] == 12000.0
    assert isinstance(job["salary_max"], float)


def test_parse_job_parses_posting_date_to_iso_day():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item())
    assert job["posting_date"] == "2026-06-01"


def test_parse_job_raw_data_captures_metadata():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item())
    raw = job["raw_data"]
    assert raw["skills"] == ["Python", "SQL"]  # blank dropped
    assert raw["salary_period"] == "Monthly"
    assert raw["employment_types"] == ["Full Time"]
    assert raw["position_levels"] == ["Senior Executive"]
    assert raw["categories"] == ["Information Technology"]
    assert raw["uuid"] == "abc-123"
    assert raw["min_experience"] == 5
    assert raw["job_post_id"] == "JOB-999"


def test_parse_job_returns_none_without_title():
    scraper = MyCareersFutureScraper()
    assert scraper._parse_job(_sample_item(title="   ")) is None


def test_parse_job_returns_none_without_uuid():
    scraper = MyCareersFutureScraper()
    assert scraper._parse_job(_sample_item(uuid="")) is None


def test_parse_job_missing_company_defaults_to_unknown():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item(postedCompany=None))
    assert job["company"] == "Unknown"


def test_parse_job_handles_missing_salary():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item(salary=None))
    assert job["salary_min"] is None
    assert job["salary_max"] is None
    # Falls back to default salary period.
    assert job["raw_data"]["salary_period"] == "Monthly"


def test_parse_job_falls_back_through_date_fields():
    scraper = MyCareersFutureScraper()
    # No newPostingDate; should fall back to createdAt.
    item = _sample_item(metadata={"createdAt": "2026-05-20T09:30:00Z"})
    job = scraper._parse_job(item)
    assert job["posting_date"] == "2026-05-20"


def test_parse_job_missing_description_yields_empty_string():
    scraper = MyCareersFutureScraper()
    job = scraper._parse_job(_sample_item(description=""))
    assert job["description"] == ""
