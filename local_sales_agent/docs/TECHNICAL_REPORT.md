# Technical report — Harvey Local AI Sales Agent

## Design and repository relationship

The assignment URL `ethanplusai/harvey` redirects to `ethanplusai/sellbird`. This GitHub repository is a fork of that upstream. Parent-level source remains under the upstream AGPL-3.0-only licence and the original root `LICENSE` and `NOTICE` are retained. The independently authored multi-product application in `local_sales_agent/` is MIT-licensed; see its own `LICENSE` and `NOTICE`.

The fork's parent `sellbird/brain.py` and configuration/setup path have been changed to accept only local Ollama inference. The assignment's multi-product business workflows and React dashboard are implemented in `local_sales_agent/` so multiple products and product-specific ICPs are stored as first-class SQLite records.

## Architecture

- React 18 + Vite dashboard: business, product, prospect, research, outreach, reply and execution log views.
- FastAPI backend: request validation, workflow orchestration, local website research, task queue and REST API.
- SQLite: businesses, products, prospects, stored research, generated outputs, local embeddings, model execution logs and retryable AI tasks.
- Ollama: sole generative inference runtime; default `qwen3:8b`.
- Sentence Transformers: local `all-MiniLM-L6-v2` embeddings for semantic retrieval.
- Research utilities: HTTPX + BeautifulSoup in the app; a separate Scrapy public-page preloader and Playwright same-host renderer for research preparation.
- Hardware helper: psutil RAM/CPU reporting, NVIDIA `nvidia-smi` detection and Apple Silicon identification. Model recommendation is a heuristic, not a performance guarantee.

## Strict inference boundary

`backend/app/local_ai.py` is the subproject's only generative inference adapter. It targets `OLLAMA_URL`, defaults to `http://127.0.0.1:11434`, disables environment proxy use, blocks non-loopback hosts, and rejects remote/cloud model tags. Model chat calls are sent only to Ollama's local `/api/chat` endpoint. There are no OpenAI, Anthropic, Gemini, Claude, Codex or paid inference SDK integrations in the multi-product app. No silent fallback or hidden provider is implemented.

The fork's parent `sellbird/brain.py` similarly instantiates the Ollama adapter only, rejects custom transports and records provider/model/duration/token counts for local runs. The parent project has historical upstream provider code and documentation in its source tree; the modified Brain/configuration path does not import those providers. The multi-product app is the recommended assignment demonstration UI.

## Data and offline separation

Public web research is separate from inference. `POST /api/research/{prospect_id}` fetches a supplied public URL while online, extracts visible page text and stores it in SQLite. It refuses localhost/private hosts and refuses redirects. If stored research already exists, it returns it immediately without contacting the website. First-time research and Scrapy/Playwright preloading require internet access; profile/ICP/signal/problem/score/email/reply workflows operate on already-stored local context.

If Ollama is unavailable, generation returns HTTP 503 and stores the exact prompt in SQLite `ai_tasks`. The dashboard's Queued AI Tasks view lists queued work and offers a manual retry after Ollama is restored. A retry stores the output in the queue for inspection; the user can rerun the original workflow to update its target record. There is no automatic background worker and no remote task service.

## Embeddings

Run `python download_embedding_model.py` online once to cache `sentence-transformers/all-MiniLM-L6-v2` under `backend/models/all-MiniLM-L6-v2`. At runtime the app loads this local path only; it does not download from Hugging Face. The model outputs 384-dimensional vectors that are normalised and stored as float32 blobs in SQLite. `POST /api/embeddings/index/{prospect_id}` indexes evidence; `POST /api/embeddings/search` uses cosine similarity to find stored prospects.

## Model and major dependency licence inventory

Licence inventory checked against project/model maintainers' published metadata on 16 November 2026. This table covers the direct major dependencies declared by this project, not every transitive package installed by pip/npm. Generate a full environment-specific SBOM before final distribution.

| Component | Role | Licence |
|---|---|---|
| Qwen3-8B (Ollama model tag `qwen3:8b`) | Local generative model | Apache-2.0 |
| Ollama | Local runtime/daemon | MIT |
| sentence-transformers/all-MiniLM-L6-v2 | Local embedding model | Apache-2.0 |
| FastAPI | Python API framework | MIT |
| Uvicorn | ASGI server | BSD-3-Clause |
| HTTPX | HTTP client | BSD-3-Clause |
| Pydantic | Data validation | MIT |
| psutil | Hardware detection | BSD-3-Clause |
| NumPy | Embedding vector operations | BSD-3-Clause project licence; bundled wheel components can carry additional notices |
| BeautifulSoup4 | HTML extraction | MIT |
| Sentence Transformers | Local embedding runtime | Apache-2.0 |
| Scrapy | Public-page preload crawler | BSD-3-Clause |
| Playwright (Python) | Browser-based public-page research helper | Apache-2.0 |
| python-multipart | CSV upload parsing | Apache-2.0 |
| pytest | Backend tests | MIT |
| React | Dashboard UI | MIT |
| React DOM | Browser renderer | MIT |
| Vite | Frontend build/dev server | MIT |
| @vitejs/plugin-react | React/Vite integration | MIT |
| lucide-react | Dashboard icons | ISC |
| SQLite | Local database engine | Public domain |

Official licence/model sources:
- Qwen3-8B model card: https://huggingface.co/Qwen/Qwen3-8B
- Ollama source licence: https://github.com/ollama/ollama/blob/main/LICENSE
- all-MiniLM-L6-v2 model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- FastAPI: https://pypi.org/project/fastapi/
- Uvicorn: https://pypi.org/project/uvicorn/
- HTTPX: https://pypi.org/project/httpx/
- Pydantic: https://pypi.org/project/pydantic/
- psutil: https://pypi.org/project/psutil/
- NumPy: https://numpy.org/doc/stable/license.html
- BeautifulSoup4: https://pypi.org/project/beautifulsoup4/
- Sentence Transformers: https://pypi.org/project/sentence-transformers/
- Scrapy: https://pypi.org/project/Scrapy/
- Playwright: https://pypi.org/project/playwright/
- python-multipart: https://pypi.org/project/python-multipart/
- pytest: https://pypi.org/project/pytest/
- React: https://www.npmjs.com/package/react
- React DOM: https://www.npmjs.com/package/react-dom
- Vite: https://www.npmjs.com/package/vite
- Vite React plugin: https://github.com/vitejs/vite-plugin-react
- lucide-react: https://www.npmjs.com/package/lucide-react

Ollama and model installation are free local software/model distribution. Hardware/electricity costs still apply. Model licence is distinct from model runtime price: no cloud inference endpoint is used.

## Hardware guidance

The app detects installed RAM and logical CPU count, tries `nvidia-smi` for an NVIDIA GPU, and detects Apple Silicon. Recommendations are intentionally conservative: below 12 GB RAM use a 4B/smaller quantised model; 12–23 GB suggests 8B; 24–47 GB suggests 14B; 48 GB+ may suit a larger model if GPU/quantisation support is adequate. The recommendation is advisory: measure memory use and tokens/second on the actual laptop.

## Test and evidence procedure

1. Install Ollama, run `ollama pull qwen3:8b`, verify `ollama list`.
2. Install backend dependencies, cache embeddings, install Playwright browser binaries if needed, and install frontend packages while online.
3. Start Ollama, FastAPI and Vite. Verify `GET /api/health` shows model installed.
4. Create a business, at least two products and prospects. Import or collect website evidence and ensure research is persisted.
5. Demonstrate business profile, each product ICP, buying signals, problem statement, scoring, email draft, reply classification, embeddings and local logs.
6. Stop Ollama and confirm the generation endpoint reports 503, stores a task, and makes no provider switch. Restart Ollama and manually retry the queued task.
7. Disconnect internet while local daemons remain running. Run `python offline_acceptance.py` from `backend/` and save terminal output plus dashboard logs.
8. Build the production React bundle and record the 5–10 minute demonstration. Do not claim offline success until the disconnected-network test has actually passed on the submission machine.

## Known limits

- Live Qwen3 inference and the full disconnected-network acceptance test have not been performed in the build environment.
- Frontend package installation timed out in the build environment, so the production build is not yet verified.
- Website research is one supplied URL in the dashboard; Scrapy/Playwright are separate preload helpers, not an integrated general discovery crawler.
- Email generation saves drafts only; email sending is intentionally not included.
- Queued AI tasks can be manually retried; there is no background queue worker and retry results do not automatically mutate the original prospect output fields.
- No live deployment or screen recording is included yet.
- Model outputs require human review; the app does not verify prospect facts independently.

## Safe research

Collect only public information that you are allowed to access. Obey robots.txt and website terms, avoid login-only pages and access-control bypasses, and do not collect unnecessary personal data. Keep the app bound to localhost. Never commit real prospect/contact data or credentials.
