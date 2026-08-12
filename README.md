# Autonomous Dropshipping Agent

A fully autonomous, multi-agent dropshipping platform designed to outperform rule-based
legacy systems. Agents are orchestrated as a cyclic, self-correcting graph via LangGraph,
reasoning over real live marketplace data rather than static heuristics.

## Architecture

Five async agents run as nodes in a LangGraph `StateGraph`:

| Agent | Model | Responsibility |
|---|---|---|
| `TrendScraperAgent` | Gemini 1.5 Flash | Extracts high-velocity consumer product signals from live web/trend sources |
| `RealLifeValidationAgent` | Claude 3.5 Sonnet | Validates candidates against live Amazon/eBay sales rank, pricing, and sentiment |
| `SupplierSourcingAgent` | Claude 3.5 Sonnet | Risk-scores supplier profiles (shipping variance, stock, disputes) |
| `DynamicListingAgent` | Claude 3.5 Sonnet | Rewrites source data into SEO-optimized listings with competitor-bounded pricing |
| `StorefrontSyncAgent` | Claude 3.5 Sonnet | Syncs finalized listings to Shopify/eBay via an abstract connector layer |

The graph includes cyclic self-correction edges: low-confidence validation loops back to
trend scraping, and rejected suppliers loop back to re-sourcing, each bounded by
`max_retries` in `PipelineState`.

All marketplace/supplier data — regardless of source — is normalized into a single
`UniversalMarketplaceItem` Pydantic schema (`src/dropship_agent/models/marketplace.py`)
before any agent reasons over it.

## Project layout

```
src/dropship_agent/
├── config/          # pydantic-settings driven configuration & API keys
├── models/          # Pydantic data contracts (marketplace, supplier, listing, graph state)
├── clients/         # thin async API clients (Anthropic, Gemini, Amazon, eBay, scraping proxy)
├── normalization/   # raw payload -> UniversalMarketplaceItem mappers
├── agents/          # the five agents described above
├── graph/           # LangGraph StateGraph wiring + self-correction routing
├── storefront/       # Shopify / eBay storefront sync connectors
└── logging_utils/   # structured JSON logging to /logs
tests/
├── unit/            # offline, mocked-client tests
└── integration/     # real ASIN/eBay item ID tests, auto-skipped without credentials
scripts/run_pipeline.py  # CLI entrypoint (supports --dry-run with fake clients)
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in real API keys
```

Required API keys (see `.env.example`): `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`,
`RAINFOREST_API_KEY` (Amazon), `EBAY_APP_ID`/`EBAY_CLIENT_SECRET`,
`SHOPIFY_STORE_DOMAIN`/`SHOPIFY_ADMIN_API_TOKEN`. `TEST_AMAZON_ASIN` and
`TEST_EBAY_ITEM_ID` are real product IDs used by the live integration tests.

## Running

```bash
python scripts/run_pipeline.py --dry-run                       # wiring smoke test, no keys needed
python scripts/run_pipeline.py --asin B0EXAMPLE --ebay-item-id "v1|123456789|0"
```

## Testing

```bash
pytest tests/unit                 # offline, no credentials required
pytest -m "not live"              # everything except live-credential tests
pytest -m live                    # real Amazon/eBay live-payload integration tests
mypy src/
ruff check src/ tests/
```

## Logging

All agent reasoning steps, API call statuses/latencies, and retry attempts are written
as structured JSON to `logs/agent_runs.log` (see `src/dropship_agent/logging_utils`).
