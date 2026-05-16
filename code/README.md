# Support Triage Agent

Terminal-based agent that triages support tickets across HackerRank, Claude, and Visa using RAG with ChromaDB + Gemini 2.5 Flash.

## How it works

```
Ticket -> Pre-Screener -> Retriever (ChromaDB) -> Confidence Check -> LLM (Gemini) -> Validator -> Output
```

The pipeline has a few key stages:

- **Pre-Screener** (`screener.py`) — regex-based filter that catches prompt injection (including French-language variants), malicious requests, off-topic questions, and pleasantries. No API call needed, fast and deterministic.

- **Indexer** (`indexer.py`) — one-time job that loads all ~774 markdown files from `data/`, splits them by heading boundaries (max 2000 chars per chunk), and stores them in a local ChromaDB collection with company/category metadata.

- **Retriever** (`retriever.py`) — semantic search over ChromaDB. Filters by company when known. When company is unknown, searches all three collections and picks the closest matches by distance.

- **Agent** (`agent.py`) — assesses retrieval confidence (HIGH/MEDIUM/LOW based on cosine distance), calls Gemini with the retrieved context, and validates the output. Falls back to escalation on any failure.

- **Prompts** (`prompts.py`) — system prompt with escalation rules, product area taxonomy, and grounding constraints. Structured JSON output format.

## Design choices

| What | Choice | Why |
|------|--------|-----|
| Vector DB | ChromaDB | Runs locally, supports metadata filtering by company |
| LLM | Gemini 2.5 Flash | Free tier available, good at classification, supports JSON mode |
| Embeddings | all-MiniLM-L6-v2 (ChromaDB default) | No API cost, runs locally |
| Framework | None (raw Python) | Easier to debug than LangChain for this scope |
| Chunking | Heading-based, 2000 char max | Keeps step-by-step instructions intact within a single chunk |
| Failure mode | Always escalate | Any error in the pipeline -> escalate rather than hallucinate |

## Setup

```bash
cd code
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Get a free Gemini API key from https://aistudio.google.com/apikey

```bash
cp .env.example .env
# then add your key: GEMINI_API_KEY=your-key-here
```

## Running

```bash
# process all tickets -> writes support_tickets/output.csv
python main.py

# process sample tickets only (for dev/testing)
python main.py --sample

# validate sample output against expected answers
python main.py --validate

# run unit tests
python tests.py
```
