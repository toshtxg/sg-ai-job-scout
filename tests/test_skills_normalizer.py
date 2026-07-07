"""Tests for pipeline.skills_normalizer canonical skill-name mapping."""

import pytest

from pipeline.skills_normalizer import normalize_skill, normalize_skills


@pytest.mark.parametrize(
    "alias,expected",
    [
        # Aliases map to their canonical form
        ("python3", "Python"),
        ("Python3", "Python"),
        ("python 3", "Python"),
        ("golang", "Go"),
        ("Golang", "Go"),
        ("js", "JavaScript"),
        ("JS", "JavaScript"),
        ("ts", "TypeScript"),
        ("pytorch", "PyTorch"),
        ("Pytorch", "PyTorch"),
        ("tf", "TensorFlow"),
        ("sklearn", "Scikit-learn"),
        ("huggingface", "Hugging Face"),
        ("ml", "Machine Learning"),
        ("Natural Language Processing", "NLP"),
        ("large language model", "LLM"),
        ("retrieval augmented generation", "RAG"),
        ("pyspark", "Spark"),
        ("amazon web services", "AWS"),
        ("google cloud", "GCP"),
        ("microsoft azure", "Azure"),
        ("postgres", "PostgreSQL"),
        ("k8s", "Kubernetes"),
        ("power bi", "Power BI"),
        ("reactjs", "React"),
        ("restful", "REST API"),
    ],
)
def test_alias_maps_to_canonical(alias, expected):
    assert normalize_skill(alias) == expected


def test_canonical_form_itself_is_stable():
    # Passing the canonical name back in returns it unchanged.
    for canonical in ["Python", "PyTorch", "AWS", "PostgreSQL", "NLP", "React"]:
        assert normalize_skill(canonical) == canonical


@pytest.mark.parametrize(
    "variant,expected",
    [
        # Casing of the input should not matter for known aliases.
        ("PYTHON", "Python"),
        ("pYtHoN", "Python"),
        ("AWS", "AWS"),
        ("aws", "AWS"),
        ("TensorFlow", "TensorFlow"),
        ("TENSORFLOW", "TensorFlow"),
    ],
)
def test_casing_is_normalized(variant, expected):
    assert normalize_skill(variant) == expected


@pytest.mark.parametrize(
    "unknown,expected",
    [
        # Unknown skills fall back to title-case, stripped.
        ("kubernetes wizardry", "Kubernetes Wizardry"),
        ("  some new tool  ", "Some New Tool"),
        ("rust", "Rust"),
        ("quantum computing", "Quantum Computing"),
    ],
)
def test_unknown_skill_falls_back_to_titlecase(unknown, expected):
    assert normalize_skill(unknown) == expected


def test_lookup_does_not_strip_whitespace_before_matching():
    # Documented edge: normalize_skill looks up skill.lower() WITHOUT stripping,
    # so a padded known alias misses the map and falls through to the title-case
    # branch. " JS " -> "Js", not "JavaScript". This pins current behavior; it is
    # deliberately NOT "fixed" here (would be a behavior change on a borderline
    # input). Callers should trim before normalizing.
    assert normalize_skill(" JS ") == "Js"
    assert normalize_skill("JS") == "JavaScript"


def test_normalize_skills_dedupes_after_normalization_preserving_order():
    skills = ["python3", "Python", "pandas", "PANDAS", "sklearn", "Scikit-learn"]
    # After normalization: Python, Python, Pandas, Pandas, Scikit-learn, Scikit-learn
    assert normalize_skills(skills) == ["Python", "Pandas", "Scikit-learn"]


def test_normalize_skills_preserves_first_appearance_order():
    skills = ["golang", "js", "python3"]
    assert normalize_skills(skills) == ["Go", "JavaScript", "Python"]


def test_normalize_skills_empty_list():
    assert normalize_skills([]) == []
