# Clawback — Developer Guide

## What is this?

AI-powered bill and contract analyser that finds every dollar you're overpaying
and drafts negotiation messages on your behalf.

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env        # add your API keys
clawback analyze "Comcast bill: Internet $89.99, TV $74.99 …"
```

## Project Layout

```
clawback/
├── models.py        # Pydantic data models
├── ai.py            # LLM abstraction (Anthropic / OpenAI)
├── analyzer.py      # Bill extraction, market comparison, overcharge detection
├── negotiator.py    # Negotiation strategy, email, phone script generation
├── cli.py           # Typer CLI with Rich output
├── api/app.py       # FastAPI REST API
└── mcp/server.py    # MCP server (FastMCP)
```

## Commands

| Command | Description |
|---------|-------------|
| `clawback analyze <bill>` | Extract + market compare + overcharge scan |
| `clawback negotiate <bill>` | Full pipeline with negotiation email |
| `clawback compare <bill>` | Market comparison only |

## Testing

```bash
python -m pytest tests/ -v
```

## API Server

```bash
uvicorn clawback.api.app:app --reload
```

## MCP Server

Configure `.mcp.json` in your editor, or run manually:

```bash
mcp run clawback/mcp/server.py
```

## Environment Variables

See `.env.example`. Key settings:

- `CLAWBACK_LLM_PROVIDER` — `anthropic` (default) or `openai`
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`
