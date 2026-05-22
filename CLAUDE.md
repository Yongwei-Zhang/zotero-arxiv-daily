# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zotero-arXiv-Daily recommends new arXiv/bioRxiv/medRxiv papers based on a user's Zotero library. It computes embedding similarity between new papers and the user's existing library, generates TLDRs via LLM, and delivers results by email. Designed to run as a GitHub Actions workflow at zero cost.

## Commands

Requires Python ≥ 3.13 (see `pyproject.toml`). `uv sync` will install a matching interpreter.

```bash
# Run the application
uv run src/zotero_arxiv_daily/main.py

# Run tests (excludes slow tests by default)
uv run pytest

# Run all tests including slow ones
uv run pytest -m ""

# Run a single test
uv run pytest tests/test_utils.py::TestGlobMatch -v

# Install/sync dependencies
uv sync
```

No linter or formatter is configured.

## Architecture

The app follows a linear pipeline orchestrated by `Executor` (`src/zotero_arxiv_daily/executor.py`):

1. **Fetch Zotero corpus** — retrieves user's library papers via pyzotero API
2. **Filter corpus** — applies `include_path` glob patterns to select relevant collections
3. **Retrieve new papers** — fetches from configured sources (arXiv RSS, bioRxiv/medRxiv REST API)
4. **Rerank** — scores candidates by weighted similarity to corpus (newer Zotero papers weighted higher)
5. **Generate TLDRs + affiliations** — via OpenAI-compatible LLM API
6. **Render + send email** — HTML email via SMTP

### Plugin Systems

**Retrievers** (`src/zotero_arxiv_daily/retriever/`): Register via `@register_retriever` decorator, discovered by `get_retriever_cls()`. Each retriever implements `_retrieve_raw_papers()` and `convert_to_paper()`.

**Rerankers** (`src/zotero_arxiv_daily/reranker/`): Register via `@register_reranker` decorator, discovered by `get_reranker_cls()`. Two implementations: `local` (sentence-transformers) and `api` (OpenAI-compatible embeddings endpoint).

### Configuration

Uses Hydra + OmegaConf. Config is composed from `config/base.yaml` (defaults) + `config/custom.yaml` (user overrides). Environment variables are interpolated via `${oc.env:VAR_NAME,default}` syntax. Entry point uses `@hydra.main`.

`config/custom.yaml` is **not checked in** — locally it's user-provided; in CI, `.github/workflows/main.yml` writes it at runtime from the `CUSTOM_CONFIG` repository variable. A missing `config/custom.yaml` is expected on a fresh clone.

### Notification side-channel (Feishu / Telegram)

After the main pipeline finishes, `Executor.run()` dumps reranked papers to `/tmp/papers.json`. `.github/workflows/main.yml` then runs `feishu_sender.py` (or `telegram_sender.py`) as a **separate step** that reads `/tmp/papers.json` and posts to the messaging API. These senders are not invoked from `main.py` — modifying notification behavior usually means editing both the sender script and the workflow step.

### Data Classes

`Paper` and `CorpusPaper` in `src/zotero_arxiv_daily/protocol.py`. `Paper` has LLM-powered methods (`generate_tldr`, `generate_affiliations`) that call the OpenAI API directly.

## Testing

Tests marked `@pytest.mark.slow` require heavy dependencies (e.g., sentence-transformers model download) and are skipped locally by default (`addopts = "-m 'not slow'"` in pyproject.toml). All other tests run with pure Python stubs (no Docker containers needed).

```bash
# Run tests (excludes slow tests)
uv run pytest

# Run all tests including slow ones
uv run pytest -m ""

# Run with coverage
uv run pytest --cov=src/zotero_arxiv_daily --cov-report=term-missing
```

## gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

Available skills: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`.

If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup` to build the binary and register skills.

## Git Workflow

- PRs should target the `dev` branch, not `main`
- Current development branch: `dev`
