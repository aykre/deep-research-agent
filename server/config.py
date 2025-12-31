import os

# Research limits
MAX_REWRITTEN_QUERIES = int(os.getenv("MAX_REWRITTEN_QUERIES", "3"))
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "10"))
MAX_RESULTS_FILTERED = int(os.getenv("MAX_RESULTS_FILTERED", "3"))
MAX_CHARACTERS_PER_PAGE = int(os.getenv("MAX_CHARACTERS_PER_PAGE", "3000"))

# Scraper configuration
USE_PLAYWRIGHT = os.getenv("USE_PLAYWRIGHT", "true").lower() == "true"
MAX_BROWSERS = int(os.getenv("MAX_BROWSERS", "1"))

# LLM configuration - Task-specific models and reasoning effort
# Writer (final response synthesis)
WRITER_LLM_MODEL = os.getenv("WRITER_LLM_MODEL", "gpt-5-mini")
WRITER_REASONING_EFFORT = os.getenv("WRITER_REASONING_EFFORT", "medium")

# Rewriter (query rewriting)
REWRITER_LLM_MODEL = os.getenv("REWRITER_LLM_MODEL", "gpt-5-mini")
REWRITER_REASONING_EFFORT = os.getenv("REWRITER_REASONING_EFFORT", "medium")

# Extractor (content extraction from web pages)
USE_EXTRACTION = os.getenv("USE_EXTRACTION", "false").lower() == "true"
EXTRACTOR_LLM_MODEL = os.getenv("EXTRACTOR_LLM_MODEL", "gpt-5-mini")
EXTRACTOR_REASONING_EFFORT = os.getenv("EXTRACTOR_REASONING_EFFORT", "low")

# Filter (search result filtering)
FILTER_LLM_MODEL = os.getenv("FILTER_LLM_MODEL", "gpt-5-mini")
FILTER_REASONING_EFFORT = os.getenv("FILTER_REASONING_EFFORT", "minimal")

# Guardrail (query safety checking)
USE_GUARDRAILS = os.getenv("USE_GUARDRAILS", "false").lower() == "true"
GUARDRAIL_LLM_MODEL = os.getenv("GUARDRAIL_LLM_MODEL", "gpt-5-mini")
GUARDRAIL_REASONING_EFFORT = os.getenv("GUARDRAIL_REASONING_EFFORT", "low")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Turnstile configuration
USE_TURNSTILE = os.getenv("USE_TURNSTILE", "false").lower() == "true"
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")
