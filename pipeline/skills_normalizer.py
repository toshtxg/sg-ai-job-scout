"""Normalize technical and soft skill names to canonical forms."""

# Mapping from lowercase variant -> canonical name.
# Every alias (including the canonical form itself, lowered) must appear as a key.
_ALIAS_MAP: dict[str, str] = {}


def _register(canonical: str, *aliases: str) -> None:
    """Register a canonical skill name and all its aliases."""
    _ALIAS_MAP[canonical.lower()] = canonical
    for alias in aliases:
        _ALIAS_MAP[alias.lower()] = canonical


# --- Programming Languages ---
_register("Python", "python 3", "python3", "Python3")
_register("Java", "java")
_register("Scala", "scala")
_register("Go", "golang", "Golang")
_register("C++", "cpp", "c/c++", "C/C++")
_register("R", "r language", "R language")
_register("JavaScript", "Javascript", "JS", "js")
_register("TypeScript", "Typescript", "TS", "ts")

# --- AI / ML Frameworks ---
_register("PyTorch", "Pytorch", "pytorch")
_register("TensorFlow", "Tensorflow", "tensorflow", "tf")
_register("Keras", "keras")
_register("Scikit-learn", "sklearn", "scikit-learn")
_register("Hugging Face", "HuggingFace", "huggingface", "hugging face")
_register("LangChain", "langchain")
_register("OpenAI", "openai")

# --- AI / ML Concepts ---
_register("Machine Learning", "ML", "ml", "machine learning")
_register("Deep Learning", "DL", "dl", "deep learning")
_register("NLP", "Natural Language Processing", "natural language processing", "nlp")
_register("Computer Vision", "CV", "cv", "computer vision")
_register("BERT", "bert")
_register("GPT", "gpt")
_register("LLM", "LLMs", "llms", "llm", "Large Language Model", "large language model")
_register("RAG", "rag", "Retrieval Augmented Generation", "retrieval augmented generation")

# --- Data Libraries ---
_register("Pandas", "pandas")
_register("NumPy", "numpy", "Numpy")
_register("Spark", "Apache Spark", "PySpark", "pyspark", "apache spark")

# --- Cloud Providers ---
_register("AWS", "Amazon Web Services", "aws", "amazon web services")
_register("GCP", "Google Cloud", "google cloud platform", "google cloud", "gcp")
_register("Azure", "Microsoft Azure", "azure", "microsoft azure")

# --- Databases ---
_register("PostgreSQL", "Postgres", "postgres", "postgresql")
_register("MySQL", "mysql")
_register("MongoDB", "mongodb", "Mongo", "mongo")
_register("Redis", "redis")
_register("Elasticsearch", "ElasticSearch", "elastic", "elasticsearch")
_register("SQL", "sql", "Sql")
_register("Snowflake", "snowflake")

# --- DevOps / Infrastructure ---
_register("Docker", "docker")
_register("Kubernetes", "K8s", "k8s")
_register("Git", "git", "GitHub", "github")
_register("CI/CD", "CICD", "cicd", "ci/cd")
_register("Airflow", "Apache Airflow", "airflow", "apache airflow")
_register("MLflow", "mlflow")

# --- Data Engineering / BI ---
_register("ETL", "etl")
_register("Data Warehouse", "data warehouse", "DWH", "dwh")
_register("dbt", "DBT")
_register("Tableau", "tableau")
_register("Power BI", "PowerBI", "power bi", "powerbi")
_register("Looker", "looker")
_register("Excel", "Microsoft Excel", "excel", "microsoft excel")
_register("SAS", "sas")
_register("SPSS", "spss")

# --- Web / API ---
_register("React", "ReactJS", "react.js", "reactjs")
_register("Node.js", "NodeJS", "node", "nodejs")
_register("REST API", "REST", "rest", "rest api", "RESTful", "restful")
_register("GraphQL", "graphql")

# --- Data Platforms ---
_register("Hadoop", "hadoop")

# --- Methodologies ---
_register("Agile", "agile", "Scrum", "scrum")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_skill(skill: str) -> str:
    """Return the canonical form of a skill name.

    If the skill is not found in the alias mapping, it is returned in
    title-case as a sensible default.
    """
    canonical = _ALIAS_MAP.get(skill.lower())
    if canonical is not None:
        return canonical
    return skill.strip().title()


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize a list of skills, removing duplicates after normalization.

    The order of first appearance is preserved.
    """
    seen: set[str] = set()
    result: list[str] = []
    for skill in skills:
        normalized = normalize_skill(skill)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
