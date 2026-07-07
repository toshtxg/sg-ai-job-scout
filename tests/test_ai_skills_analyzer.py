"""Tests for pipeline.ai_skills_analyzer taxonomy matching and aggregation."""

from pipeline.ai_skills_analyzer import (
    analyze_all_listings,
    analyze_listing,
    analyze_text,
    classify_ai_involvement,
)


def test_analyze_text_matches_keywords_by_category():
    text = "We build RAG pipelines with LangChain and fine-tuning on embeddings."
    result = analyze_text(text)
    assert "LLM & GenAI Development" in result
    matched = result["LLM & GenAI Development"]
    assert "rag" in matched
    assert "langchain" in matched
    assert "fine-tuning" in matched
    assert "embeddings" in matched


def test_analyze_text_is_case_insensitive():
    assert "Deep Learning" in analyze_text("Experience with PYTORCH and Neural Networks")


def test_analyze_text_uses_word_boundaries_no_substring_false_positive():
    # "nlp" must not match inside a larger word; "enlplace" is nonsense but proves
    # the \b boundary. A plain word "planning" must not trigger "nlp".
    result = analyze_text("strategic planning and stakeholder management")
    assert "NLP" not in result


def test_analyze_text_no_matches_returns_empty_dict():
    assert analyze_text("We sell artisanal coffee and pastries.") == {}


def test_analyze_listing_combines_description_and_skills():
    # The keyword lives only in the skills list, not the description.
    result = analyze_listing("Generic backend role.", technical_skills=["XGBoost"])
    assert "Classical ML" in result
    assert "xgboost" in result["Classical ML"]


def test_analyze_listing_handles_none_description():
    result = analyze_listing(None, technical_skills=["Computer Vision"])
    assert "Computer Vision" in result


def test_classify_ai_involvement_maps_categories_to_levels():
    categories = {
        "LLM & GenAI Development": ["rag"],
        "Classical ML": ["xgboost"],
    }
    levels = classify_ai_involvement(categories)
    assert "AI/LLM Engineering" in levels  # from LLM & GenAI Development
    assert "Uses ML models" in levels       # from Classical ML
    assert "MLOps & Infrastructure" not in levels


def test_classify_ai_involvement_empty_when_no_categories():
    assert classify_ai_involvement({}) == []


def test_analyze_all_listings_aggregates_counts_and_keywords():
    listings = [
        # Two listings mention pytorch (Deep Learning); one mentions rag (LLM).
        {"id": 1, "description": "pytorch neural network work", "technical_skills": []},
        {"id": 2, "description": "pytorch and rag systems", "technical_skills": []},
        {"id": 3, "description": "we roast coffee beans", "technical_skills": []},
    ]
    out = analyze_all_listings(listings)

    assert out["total_analyzed"] == 3
    assert out["listings_with_ai"] == 2  # listing 3 has no AI keywords

    counts = out["category_counts"]
    assert counts["Deep Learning"] == 2
    assert counts["LLM & GenAI Development"] == 1

    # Keyword tallies per category.
    assert out["category_keywords"]["Deep Learning"]["pytorch"] == 2

    # listing ids grouped by category.
    assert set(out["listings_by_category"]["Deep Learning"]) == {1, 2}
    assert out["listings_by_category"]["LLM & GenAI Development"] == [2]


def test_analyze_all_listings_supports_listing_id_key():
    # analyze_all_listings falls back to "listing_id" when "id" is absent.
    listings = [{"listing_id": "abc", "description": "spacy and ner", "technical_skills": []}]
    out = analyze_all_listings(listings)
    assert out["listings_by_category"]["NLP"] == ["abc"]


def test_analyze_all_listings_empty_input():
    out = analyze_all_listings([])
    assert out["total_analyzed"] == 0
    assert out["listings_with_ai"] == 0
    assert out["category_counts"] == {}
    assert out["category_keywords"] == {}
    assert out["listings_by_category"] == {}
