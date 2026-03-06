# Web-page

This is a lightweight CLI agent that takes a topic, searches the web, extracts key information, and produces a one-page summary in Markdown.

## Expanded Stack
- Backend API: FastAPI + SQLite (background report generation)
- Retrieval enhancement: domain filtering, dedup, snippet extraction
- Multi-stage pipeline: retrieval → compression → outline → synthesis
- Frontend: React + Vite + Tailwind
- Multi-model: provider/model routing via request params (per-stage override optional)

## What It Does
- Searches the web for the topic
- Visits top results to extract key points
- Generates a concise summary with citations
- Saves the summary to `outputs/<topic>.md`

## Setup
1. Create a virtual environment (optional)
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set an HF token if you use the Hugging Face Inference API:

```bash
export HF_TOKEN=YOUR_TOKEN
```

## Usage

```bash
python web_collect_agent.py "your topic"
```

Common options:
- `--lang zh|en` Output language
- `--min-sources 3` Minimum sources to cite
- `--max-results 8` Max web search results to scan
- `--output outputs/custom.md` Output file path
- `--model-id <hf-model-id>` Override HF model id
- `--provider <provider>` Override inference provider

## Output
The agent writes a Markdown file containing:
- Title
- Overview paragraph
- Key points with citations
- Notable stats (if any)
- Sources list

## Simple Web UI
Run the minimal Flask UI:

```bash
python web_ui.py
```

Then open `http://localhost:8000` in your browser.

## FastAPI + React UI
Backend:

```bash
python -m uvicorn backend.app:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend reads the API base from `VITE_API_BASE` (defaults to `http://localhost:8000`).

## Pipeline Stages
1. Retrieval: search + visit pages and collect snippets.
2. Compression: per-source evidence bullets.
3. Outline: structured report plan.
4. Synthesis: final one-page report.

## Evaluation Module
Single report evaluation (heuristics + optional LLM judge):

```bash
curl -X POST http://localhost:8000/api/evals \\
  -H 'Content-Type: application/json' \\
  -d '{\"report_id\": \"<report_id>\", \"min_sources\": 3}'
```

Batch evaluation uses a dataset JSON file:

```bash
curl -X POST http://localhost:8000/api/evals/batch \\
  -H 'Content-Type: application/json' \\
  -d '{\"dataset_path\": \"backend/eval_dataset.sample.json\"}'
```
## Notes
- The agent uses `WebSearchTool` and `VisitWebpageTool` from smolagents.
- Output length is constrained to roughly one page.
