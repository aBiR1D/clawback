# 🦞 Clawback

**AI-powered bill & contract analyzer** — find every dollar you're overpaying
and get negotiation messages drafted automatically.

## How It Works

1. **Paste / upload** a bill or contract
2. **AI extracts** every line item and fee
3. **Compares** to current market rates
4. **Identifies** overcharges and hidden fees
5. **Generates** negotiation emails and phone scripts
6. **Tracks** your total potential savings

## Installation

```bash
git clone <repo-url> && cd clawback
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # add your LLM API key
```

## Usage

### CLI

```bash
# Analyze a bill
clawback analyze "Comcast: Internet $89.99, Cable TV $74.99, Sports Fee $12.99"

# Full negotiation pipeline
clawback negotiate path/to/bill.txt

# Market comparison only
clawback compare path/to/invoice.pdf
```

### REST API

```bash
uvicorn clawback.api.app:app --reload
# POST http://localhost:8000/api/v1/analyze   { "text": "..." }
# POST http://localhost:8000/api/v1/negotiate { "text": "..." }
# GET  http://localhost:8000/health
```

### MCP Server

Add to your editor's `.mcp.json`:

```json
{
  "mcpServers": {
    "clawback": {
      "command": "uv",
      "args": ["run", "--directory", ".", "mcp", "run", "clawback/mcp/server.py"]
    }
  }
}
```

**Tools exposed:** `analyze_bill`, `negotiate_bill`, `find_savings`

## Development

```bash
python -m pytest tests/ -v   # run tests
ruff check clawback/         # lint
```

## License

MIT
