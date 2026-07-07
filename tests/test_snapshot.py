"""Tests for pipeline.snapshot market-aggregation math.

A fake Supabase client feeds synthetic classified rows into generate_snapshot
and captures the upserted snapshot. Expected aggregates are hand-computed from
the synthetic inputs (not echoed from the function) so a regression in the math
is actually caught.
"""

from datetime import datetime, timedelta

from pipeline.snapshot import generate_snapshot


class _Response:
    def __init__(self, data):
        self.data = data


class _Query:
    """Records the chained call and returns preset page data on execute()."""

    def __init__(self, pages_by_table, table_name, upsert_sink):
        self._pages_by_table = pages_by_table
        self._table = table_name
        self._upsert_sink = upsert_sink
        self._is_upsert = False
        self._upsert_payload = None

    def select(self, *_args, **_kwargs):
        return self

    def range(self, start, end):
        # Serve the whole dataset as a single page. The caller stops paging when
        # a page is shorter than page_size, which one full page satisfies.
        self._range = (start, end)
        return self

    def upsert(self, payload, **_kwargs):
        self._is_upsert = True
        self._upsert_payload = payload
        return self

    def execute(self):
        if self._is_upsert:
            self._upsert_sink.append(self._upsert_payload)
            return _Response([self._upsert_payload])
        start, _end = getattr(self, "_range", (0, None))
        rows = self._pages_by_table.get(self._table, [])
        # Only the first range() call (offset 0) yields rows; later offsets are
        # empty. Since we serve everything at once and it is < page_size, the
        # snapshot loop breaks after the first page anyway.
        return _Response(rows if start == 0 else [])


class FakeSupabase:
    def __init__(self, pages_by_table):
        self._pages_by_table = pages_by_table
        self.upserts = []

    def table(self, name):
        return _Query(self._pages_by_table, name, self.upserts)


def _make_row(role, seniority, tech_skills, raw):
    return {
        "role_category": role,
        "seniority_level": seniority,
        "technical_skills": tech_skills,
        "raw_listings": raw,
    }


def test_empty_dataset_returns_only_snapshot_date():
    client = FakeSupabase({"classified_listings": []})
    result = generate_snapshot(client)
    assert set(result.keys()) == {"snapshot_date"}
    assert client.upserts == []  # nothing stored


def test_full_aggregation_math():
    rows = [
        _make_row(
            "Data Scientist", "Senior", ["Python", "SQL"],
            {"salary_min": 5000, "salary_max": 8000, "posting_date": "2020-01-01"},
        ),
        _make_row(
            "Data Scientist", "Mid", ["Python"],
            {"salary_min": 7000, "salary_max": None, "posting_date": "2020-01-01"},
        ),
        _make_row(
            "Data Analyst", "Junior", ["SQL", "Excel"],
            {"salary_min": 4000, "salary_max": 6000, "posting_date": "2020-01-01"},
        ),
    ]
    client = FakeSupabase({"classified_listings": rows})
    snap = generate_snapshot(client)

    assert snap["total_listings"] == 3

    # Role counts
    assert snap["listings_by_role"] == {"Data Scientist": 2, "Data Analyst": 1}
    # Seniority counts
    assert snap["listings_by_seniority"] == {"Senior": 1, "Mid": 1, "Junior": 1}

    # Top skills: Python x2, SQL x2, Excel x1. Use dict for order-insensitive check.
    top = {item["skill"]: item["count"] for item in snap["top_skills"]}
    assert top == {"Python": 2, "SQL": 2, "Excel": 1}

    # Average salary by role — hand computed.
    # Data Scientist: mins [5000, 7000] -> avg_min 6000.0; maxs [8000] -> avg_max 8000.0
    #   count = max(len mins=2, len maxs=1) = 2
    ds = snap["avg_salary_by_role"]["Data Scientist"]
    assert ds == {"avg_min": 6000.0, "avg_max": 8000.0, "count": 2}
    # Data Analyst: mins [4000] -> 4000.0; maxs [6000] -> 6000.0; count 1
    da = snap["avg_salary_by_role"]["Data Analyst"]
    assert da == {"avg_min": 4000.0, "avg_max": 6000.0, "count": 1}

    # These old postings are far outside the 7-day window.
    assert snap["new_listings_count"] == 0

    # It was upserted exactly once.
    assert client.upserts == [snap]


def test_missing_fields_use_defaults():
    # Rows without role/seniority default to "Other"/"Mid"; missing skills ignored.
    rows = [
        {"raw_listings": {}},  # no role, no seniority, no skills, no salary
        {"role_category": "AI Engineer", "raw_listings": None},
    ]
    client = FakeSupabase({"classified_listings": rows})
    snap = generate_snapshot(client)

    assert snap["total_listings"] == 2
    assert snap["listings_by_role"] == {"Other": 1, "AI Engineer": 1}
    assert snap["listings_by_seniority"] == {"Mid": 2}
    assert snap["top_skills"] == []
    # No salary data anywhere -> empty avg map.
    assert snap["avg_salary_by_role"] == {}


def test_new_listings_count_uses_7_day_window():
    recent = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    rows = [
        _make_row("Data Analyst", "Mid", [], {"posting_date": recent}),
        _make_row("Data Analyst", "Mid", [], {"posting_date": old}),
        _make_row("Data Analyst", "Mid", [], {"posting_date": None}),
    ]
    client = FakeSupabase({"classified_listings": rows})
    snap = generate_snapshot(client)
    assert snap["new_listings_count"] == 1
