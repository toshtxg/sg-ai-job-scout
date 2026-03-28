"""
AI Skills Taxonomy Analyzer

Scans job descriptions and classified skills to categorize AI capabilities
into meaningful subcategories, tracking what employers actually want.
"""

import re
from collections import Counter

# Each category maps to a list of keywords/phrases (lowercased for matching).
# Match against both job descriptions and extracted technical_skills.

AI_SKILLS_TAXONOMY = {
    "AI Literacy & Augmentation": [
        "ai tools", "ai-powered", "ai-assisted", "ai-enhanced",
        "chatgpt", "microsoft copilot", "github copilot", "claude",
        "gemini", "ai literacy", "ai fluency", "generative ai tools",
        "ai productivity", "leverage ai", "use of ai", "ai-augmented",
        "ai for business", "ai for marketing", "ai for hr",
        "ai assistants", "copilot",
    ],
    "Prompt Engineering": [
        "prompt engineering", "prompt design", "prompt optimization",
        "few-shot learning", "few-shot prompting", "few shot",
        "chain-of-thought", "chain of thought", "system prompts",
        "prompt templates", "instruction tuning", "prompt tuning",
        "in-context learning", "prompt management", "prompt versioning",
        "prompt injection",
    ],
    "LLM & GenAI Development": [
        "llm", "large language model", "foundation model",
        "rag", "retrieval augmented generation", "retrieval-augmented",
        "vector database", "pinecone", "weaviate", "chroma", "faiss",
        "milvus", "qdrant", "embeddings", "text embeddings",
        "fine-tuning", "fine-tune", "fine tuning", "peft", "lora", "qlora",
        "langchain", "llamaindex", "llama index", "haystack",
        "semantic search", "gpt api", "openai api", "claude api",
        "gemini api", "hugging face", "huggingface",
        "token optimization", "context window", "hallucination",
        "grounding", "generative ai", "genai",
    ],
    "AI Agents & Automation": [
        "ai agent", "ai agents", "agentic ai", "agentic workflow",
        "agentic", "autonomous agent", "multi-agent", "multi agent",
        "agent orchestration", "agent framework",
        "tool use", "function calling", "tool calling",
        "autogpt", "crewai", "autogen", "langgraph",
        "agent memory", "agent planning", "workflow automation",
        "reasoning agent", "react agent", "mcp",
        "model context protocol",
    ],
    "AI Evaluation & Safety": [
        "model evaluation", "eval framework", "evals",
        "red teaming", "red-teaming", "adversarial testing",
        "ai safety", "ai security", "bias detection", "fairness testing",
        "algorithmic bias", "guardrails", "safety guardrails",
        "content filtering", "jailbreak prevention",
        "benchmark", "benchmarking", "model benchmarks",
        "rlhf", "reinforcement learning from human feedback",
        "alignment", "model alignment", "toxicity detection",
        "harmful content", "ai risk assessment", "model risk",
    ],
    "Classical ML": [
        "machine learning", "scikit-learn", "sklearn",
        "xgboost", "lightgbm", "catboost",
        "feature engineering", "feature selection", "feature store",
        "a/b testing", "experimentation platform",
        "regression", "classification", "clustering",
        "random forest", "gradient boosting", "decision tree",
        "hyperparameter tuning", "cross-validation",
        "model selection", "model interpretability", "shap", "lime",
        "statistical modeling", "predictive modeling",
        "time series", "forecasting", "anomaly detection",
    ],
    "Deep Learning": [
        "deep learning", "neural network", "neural networks",
        "pytorch", "tensorflow", "keras", "jax",
        "cnn", "convolutional neural network",
        "rnn", "lstm", "gru", "recurrent neural network",
        "gan", "generative adversarial",
        "attention mechanism", "self-attention",
        "transfer learning", "pre-trained model",
        "gpu training", "distributed training", "multi-gpu",
        "backpropagation", "gradient descent",
    ],
    "NLP": [
        "natural language processing", "nlp",
        "transformers", "transformer architecture",
        "bert", "roberta", "t5",
        "text classification", "sentiment analysis",
        "named entity recognition", "ner",
        "text processing", "text preprocessing", "tokenization",
        "information extraction", "text mining",
        "machine translation", "question answering",
        "document understanding", "document processing",
        "speech recognition", "speech-to-text", "asr",
        "spacy", "nltk",
    ],
    "Computer Vision": [
        "computer vision", "image classification", "image recognition",
        "object detection", "yolo", "faster r-cnn", "ssd",
        "image segmentation", "semantic segmentation",
        "instance segmentation", "ocr", "optical character recognition",
        "opencv", "vision transformer", "vit",
        "video analysis", "video processing",
        "pose estimation", "face detection", "facial recognition",
        "point cloud", "3d vision", "depth estimation",
        "medical imaging",
    ],
    "MLOps & Infrastructure": [
        "mlops", "ml ops", "machine learning operations",
        "model deployment", "model serving", "model monitoring",
        "mlflow", "kubeflow",
        "model registry", "model versioning",
        "ci/cd for ml", "ml pipeline", "ml workflow",
        "model drift", "data drift", "concept drift",
        "feature store", "feast",
        "experiment tracking", "model reproducibility",
        "seldon", "bentoml", "tfserving", "triton inference",
        "sagemaker", "vertex ai", "azure ml",
        "llmops",
        "evidently", "whylabs",
    ],
    "Responsible AI & Governance": [
        "responsible ai", "ethical ai", "ai ethics",
        "ai governance", "ai policy", "ai regulation",
        "ai compliance", "eu ai act", "ai risk management",
        "algorithmic accountability", "algorithmic transparency",
        "explainable ai", "xai", "model explainability",
        "ai audit", "fairness", "bias mitigation", "debiasing",
        "ai impact assessment", "ai risk framework",
        "nist ai rmf", "model documentation", "model card",
        "ai trustworthiness", "human oversight",
    ],
}

# Precompile regex patterns for each category
_CATEGORY_PATTERNS: dict[str, list[re.Pattern]] = {}
for category, keywords in AI_SKILLS_TAXONOMY.items():
    _CATEGORY_PATTERNS[category] = [
        re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kw in keywords
    ]

# Tier classification for the UI
SKILL_TIERS = {
    "Tier 1: Foundational": [
        "AI Literacy & Augmentation",
        "Prompt Engineering",
    ],
    "Tier 2: Professional": [
        "Classical ML",
        "Deep Learning",
        "NLP",
        "MLOps & Infrastructure",
        "LLM & GenAI Development",
    ],
    "Tier 3: Specialist": [
        "AI Agents & Automation",
        "AI Evaluation & Safety",
        "Computer Vision",
        "Responsible AI & Governance",
    ],
}

# AI involvement levels — maps taxonomy categories to user-facing buckets
AI_INVOLVEMENT_LEVELS = {
    "Uses AI to augment": [
        "AI Literacy & Augmentation",
        "Prompt Engineering",
    ],
    "Uses ML models": [
        "Classical ML",
        "Deep Learning",
        "NLP",
        "Computer Vision",
    ],
    "AI/LLM Engineering": [
        "LLM & GenAI Development",
        "AI Agents & Automation",
        "AI Evaluation & Safety",
        "Responsible AI & Governance",
    ],
    "MLOps & Infrastructure": [
        "MLOps & Infrastructure",
    ],
}


def classify_ai_involvement(listing_categories: dict[str, list[str]]) -> list[str]:
    """Given a listing's matched AI categories, return its AI involvement levels."""
    levels = []
    matched_cats = set(listing_categories.keys())
    for level, cats in AI_INVOLVEMENT_LEVELS.items():
        if matched_cats & set(cats):
            levels.append(level)
    return levels


# Maturity labels
SKILL_MATURITY = {
    "AI Literacy & Augmentation": "Becoming table stakes",
    "Prompt Engineering": "Explosive growth (135% YoY)",
    "LLM & GenAI Development": "Strong growth, highest salary ceiling",
    "AI Agents & Automation": "Fastest emerging (46% CAGR)",
    "AI Evaluation & Safety": "Emerging, critical talent gap",
    "Classical ML": "Established foundation",
    "Deep Learning": "Established, steady demand",
    "NLP": "Established, surging with GenAI",
    "Computer Vision": "Established niche",
    "MLOps & Infrastructure": "Critical bottleneck (9.8x growth)",
    "Responsible AI & Governance": "Regulatory-driven growth",
}


def analyze_text(text: str) -> dict[str, list[str]]:
    """
    Scan text for AI skill keywords. Returns dict of category -> matched keywords.
    """
    results: dict[str, list[str]] = {}
    text_lower = text.lower()

    for category, patterns in _CATEGORY_PATTERNS.items():
        matched = []
        for pattern, keyword in zip(patterns, AI_SKILLS_TAXONOMY[category]):
            if pattern.search(text_lower):
                matched.append(keyword)
        if matched:
            results[category] = matched

    return results


def analyze_listing(
    description: str, technical_skills: list[str] | None = None
) -> dict[str, list[str]]:
    """
    Analyze a single listing's description + skills for AI skill categories.
    """
    # Combine description and skills into one searchable text
    combined = description or ""
    if technical_skills:
        combined += " " + " ".join(technical_skills)
    return analyze_text(combined)


def analyze_all_listings(listings: list[dict]) -> dict:
    """
    Analyze all classified listings and return aggregate stats.

    Each listing should have: description (from raw_listings),
    technical_skills (from classified_listings).

    Returns:
    {
        "category_counts": {category: count},
        "category_keywords": {category: {keyword: count}},
        "listings_by_category": {category: [listing_ids]},
        "total_analyzed": int,
        "listings_with_ai": int,
    }
    """
    category_counts = Counter()
    category_keywords: dict[str, Counter] = {
        cat: Counter() for cat in AI_SKILLS_TAXONOMY
    }
    listings_by_category: dict[str, list] = {
        cat: [] for cat in AI_SKILLS_TAXONOMY
    }
    listings_with_ai = 0

    for listing in listings:
        desc = listing.get("description") or ""
        skills = listing.get("technical_skills") or []
        listing_id = listing.get("id") or listing.get("listing_id")

        matches = analyze_listing(desc, skills)

        if matches:
            listings_with_ai += 1

        for category, keywords in matches.items():
            category_counts[category] += 1
            for kw in keywords:
                category_keywords[category][kw] += 1
            if listing_id:
                listings_by_category[category].append(listing_id)

    return {
        "category_counts": dict(category_counts.most_common()),
        "category_keywords": {
            cat: dict(counter.most_common(20))
            for cat, counter in category_keywords.items()
            if counter
        },
        "listings_by_category": {
            cat: ids for cat, ids in listings_by_category.items() if ids
        },
        "total_analyzed": len(listings),
        "listings_with_ai": listings_with_ai,
    }
