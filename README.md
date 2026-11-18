# Harvey Local AI Sales Agent

A local-first extension of the Harvey/Sellbird starter for EDXSO Assignment 2. The working branch replaces the parent project's active Claude/Codex Brain with local Ollama inference and includes a dedicated multi-product application under `local_sales_agent/`.

## Local multi-product application

The multi-product app is self-contained in `local_sales_agent/`. It provides:

- Business and multiple-product configuration in SQLite.
- Product-specific ideal customer profiles.
- Prospect creation and CSV import.
- Public website evidence collection and local storage.
- Buying-signal classification and prospect-specific problem statements.
- Prospect scoring, personalised email drafts and reply classification.
- Local Sentence Transformers embeddings and semantic retrieval.
- Hardware detection, local execution logs and explicit Ollama-unavailable errors.
- A React/Vite dashboard with no paid LLM service or cloud inference dependency.

## Run on Windows

### 1. Prepare Ollama

Install Ollama from https://ollama.com/download, then in PowerShell:

```powershell
ollama pull qwen3:0.6b
ollama list
```

### 2. Start the backend

```powershell
cd local_sales_agent\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_embedding_model.py
playwright install chromium
$env:OLLAMA_MODEL = "qwen3:0.6b"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Start the dashboard

Open a second PowerShell terminal:

```powershell
cd local_sales_agent\frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Backend health is at http://127.0.0.1:8000/api/health.

### 4. Offline acceptance test

Before disconnecting the internet, prepare a business, at least two products, prospects and stored research evidence. Download the Ollama model, Python/npm dependencies and the Sentence Transformers checkpoint. Then disconnect the internet while leaving Ollama, FastAPI and Vite running. Run:

```powershell
cd local_sales_agent\backend
python offline_acceptance.py
```

The app reuses stored research while offline. First-time public website research and dependency/model downloads require internet access.

## Parent Sellbird/Harvey code

The repository was forked from `ethanplusai/sellbird`, which is the current destination of the assignment's `ethanplusai/harvey` URL. The parent source remains subject to its original AGPL-3.0-only licence and retains its upstream notices. Its active Brain/configuration/setup path has been changed to local Ollama only; non-Ollama providers and custom transports are rejected.

The independently authored `local_sales_agent/` subproject is MIT-licensed. Its licence and dependency/model disclosures are included in that directory. Do not remove or replace the parent's root `LICENSE` or upstream `NOTICE`.

## Current verification and honest limitations

- The multi-product backend's automated smoke tests pass: 4 tests.
- Python syntax compilation passes for the backend, offline acceptance script and research helpers.
- Live Qwen3 inference has not yet been verified on the target computer.
- The full offline acceptance test has not yet been performed with internet disconnected.
- The frontend production build has not yet been verified.
- Scrapy and Playwright are provided for public-page research preloading; use only permitted public pages and obey robots/site usage rules.
- Emails are generated as drafts only; this local multi-product app does not send email.
- Failed AI prompts are saved in a local SQLite queue and can be retried manually from the dashboard; there is no automatic background worker.
- No hosted deployment or demonstration recording is included yet.

See `local_sales_agent/README.md`, `local_sales_agent/docs/TECHNICAL_REPORT.md`, `local_sales_agent/docs/IMPLEMENTATION_STATUS.md` and `local_sales_agent/docs/OFFLINE_ACCEPTANCE.md` for the detailed setup, licence inventory, test procedure and known gaps.
