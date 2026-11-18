# Harvey Local AI Sales Agent — multi-product application

This folder contains the independently authored local-first multi-product application included alongside the modified Harvey/Sellbird parent project.

## Run on Windows

1. Install Ollama from https://ollama.com/download.
2. In PowerShell run `ollama pull qwen3:0.6b`.
3. Backend:

```powershell
cd local_sales_agent\backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python download_embedding_model.py
playwright install chromium
$env:OLLAMA_MODEL = "qwen3:0.6b"
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

4. In a second PowerShell window:

```powershell
cd local_sales_agent\frontend
npm install
npm run dev
```

5. Open http://127.0.0.1:5173. API health: http://127.0.0.1:8010/api/health.

## Workflow

Create a business and multiple products, import prospects via CSV or enter them manually, collect public website research while online, and run profile, product ICP, buying-signal classification, problem statement, score, email draft and reply classification. Local Sentence Transformers embeddings support semantic retrieval. The React dashboard has execution logs and hardware/model status.

## Offline preparation and proof

Download Ollama model weights, Python/Node dependencies, embedding checkpoint and Playwright Chromium while online. Create business/product/prospect records and store research before disconnecting. Leave Ollama, FastAPI and Vite running on localhost, disconnect the internet and run:

```powershell
cd local_sales_agent\backend
python offline_acceptance.py
```

Do not count the offline test as passed until this has been performed on the target machine with a real model.

## Local-only boundary

`backend/app/local_ai.py` is the only inference adapter. It rejects non-loopback Ollama endpoints and cloud/remote model tags, disables environment proxy use, and returns HTTP 503 when local inference is unavailable. There is no cloud fallback. Public website retrieval is separated from inference and only uses user-supplied public websites.

## Licensing and limits

This subproject is MIT-licensed under `LICENSE`. The parent Sellbird/Harvey source remains AGPL-3.0-only; do not remove the parent licence or NOTICE. Qwen3-0.6B and all-MiniLM-L6-v2 model cards identify Apache-2.0. See `docs/TECHNICAL_REPORT.md` for dependency licences and verification procedure.

Known limitations as of 18 November 2026: a live Qwen3 0.6B response and a business-profile generation through FastAPI have been observed on the target Windows laptop; the successful business-profile inference was logged at approximately 342 seconds, so generation is slow on the 3.9 GB RAM / Celeron test machine. Business and two product records were created successfully; a final read-back of the saved business profile and product ICPs remains outstanding. Prospect qualification workflows are implemented in code but have not yet been demonstrated end-to-end on the target machine. The React production build, local embeddings installation, complete disconnected-network acceptance and demo recording are outstanding. Email generation is draft-only; the SQLite task queue uses manual retry and has no automatic worker. Initial public-web research requires internet; offline research must reuse evidence stored beforehand.
