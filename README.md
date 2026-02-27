# Web-page

This is a lightweight CLI agent that takes a topic, searches the web, extracts key information, and produces a one-page summary in Markdown.

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

## Notes
- The agent uses `WebSearchTool` and `VisitWebpageTool` from smolagents.
- Output length is constrained to roughly one page.
