# Deep Research

An AI-powered research assistant that conducts comprehensive web research using a multi-agent workflow. The system intelligently searches, scrapes, extracts, and synthesizes information to provide detailed research reports.

Only supports OpenAI models.

## Features

- Multi-agent research workflow
- Intelligent query rewriting
- Web scraping (supports both Playwright and BeautifulSoup4)
- Smart content extraction
- Real-time updates
- Optional query guardrails
- Optional bot protection (via Cloudflare Turnstile)

## Technologies Used

### Backend
- FastAPI
- LangChain
- LangGraph
- Playwright
- BeautifulSoup4
- DuckDuckGo Search

### Frontend
- React
- TypeScript
- Vite
- Tailwind CSS
- React Markdown

## Configuration Options

### Environment Configuration

Copy the example environment file and configure:

```bash
cp .env.example .env
cp web/.env.example web/.env
```

Edit `.env` and set your configuration:

```bash
# Required: OpenAI API key
OPENAI_API_KEY=your_openai_api_key

# Optional: Research limits
MAX_REWRITTEN_QUERIES=9
MAX_RESULTS_PER_QUERY=10
MAX_RESULTS_FILTERED=3
MAX_CHARACTERS_PER_PAGE=3000

# Optional: Scraper configuration
USE_PLAYWRIGHT=true
MAX_BROWSERS=1

# Optional: Task-specific LLM models and reasoning effort
# Writer (final response synthesis)
WRITER_LLM_MODEL=gpt-5-mini
WRITER_REASONING_EFFORT=medium

# Rewriter (query rewriting)
REWRITER_LLM_MODEL=gpt-5-mini
REWRITER_REASONING_EFFORT=medium

# Extractor (content extraction)
USE_EXTRACTION=false
EXTRACTOR_LLM_MODEL=gpt-5-nano
EXTRACTOR_REASONING_EFFORT=low

# Filter (search result filtering)
FILTER_LLM_MODEL=gpt-5-nano
FILTER_REASONING_EFFORT=minimal

# Optional: Query Guardrails (safety checks)
USE_GUARDRAILS=false
GUARDRAIL_LLM_MODEL=gpt-5-mini
GUARDRAIL_REASONING_EFFORT=low

# Optional: Cloudflare Turnstile (for bot protection)
USE_TURNSTILE=false
TURNSTILE_SECRET_KEY=your_turnstile_secret
```

For the frontend, create `web/.env`:

```bash
# Optional: Enable Cloudflare Turnstile
VITE_USE_TURNSTILE=false
VITE_TURNSTILE_SITE_KEY=your_site_key
```

### Research Parameters

- `MAX_REWRITTEN_QUERIES`: Number of follow-up query iterations (default: 9)
- `MAX_RESULTS_PER_QUERY`: Search results to fetch per query (default: 10)
- `MAX_RESULTS_FILTERED`: Results to keep after relevance filtering (default: 3)
- `MAX_CHARACTERS_PER_PAGE`: The maximum number of characters from each page to pass to the LLM at various stages (default: 3000)

### Scraping Options

- `USE_PLAYWRIGHT`: Use Playwright (default: true)
  - Set to `false` to use BeautifulSoup4 only (faster, but can't handle JS)
- `MAX_BROWSERS`: Number of concurrent browser instances (default: 1)

### LLM Models and Reasoning Effort

Configure task-specific models and reasoning effort levels:

#### Writer (Final Response Synthesis)
- `WRITER_LLM_MODEL`: Model for synthesizing final research response (default: gpt-5-mini)
- `WRITER_REASONING_EFFORT`: Reasoning effort level - minimal, low, medium, high (default: medium)

#### Rewriter (Query Rewriting)
- `REWRITER_LLM_MODEL`: Model for generating follow-up queries (default: gpt-5-mini)
- `REWRITER_REASONING_EFFORT`: Reasoning effort level (default: medium)

#### Extractor (Content Extraction)
- `USE_EXTRACTION`: Set to "true" to enable LLM-based content extraction (default: false)
- `EXTRACTOR_LLM_MODEL`: Model for extracting structured content from web pages (default: gpt-5-mini)
- `EXTRACTOR_REASONING_EFFORT`: Reasoning effort level (default: low)

#### Filter (Search Result Filtering)
- `FILTER_LLM_MODEL`: Model for filtering search results by relevance (default: gpt-5-mini)
- `FILTER_REASONING_EFFORT`: Reasoning effort level (default: minimal)

#### Guardrails (Query Safety Checking)
- `USE_GUARDRAILS`: Enable query safety checks before research begins (default: false)
- `GUARDRAIL_LLM_MODEL`: Model for evaluating query safety (default: gpt-5-mini)
- `GUARDRAIL_REASONING_EFFORT`: Reasoning effort level (default: low)

## Installation

### Clone the Repository

```bash
git clone https://github.com/aykre/deep-research-agent
cd deep-research
```

### Backend Setup

Install Python dependencies using `uv`:

```bash
# Install uv if you haven't already
pip install uv

# Install project dependencies
uv sync
```

Install Playwright browsers (if using Playwright scraper):

```bash
uv run playwright install --with-deps chromium
```

### Frontend Setup

```bash
cd web
npm install
```

## Running the Application

### Development Mode

Backend:

```bash
# From project root
uv run server
```

The API will be available at `http://localhost:8000`

Frontend:

```bash
cd web
npm run dev
```

The UI will be available at `http://localhost:5173`

### Production Build

Frontend:

```bash
cd web
npm run build
npm run preview
```

## Docker Support

Docker configuration is included for containerized deployment:

```bash
docker compose up -d --build
```
