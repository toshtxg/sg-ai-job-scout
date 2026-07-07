"""Shared pytest fixtures and import-time setup for the pipeline test suite.

`pipeline.classifier` reads OPENAI_API_KEY and constructs an OpenAI client at
import time. Set a dummy key here — conftest is imported before any test module
in this directory, so the env var is in place before `import pipeline.classifier`
runs. No network call is made by the tests; the OpenAI client is monkeypatched
where the classifier is exercised.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
