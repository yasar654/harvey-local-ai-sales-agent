# Implementation status and acceptance evidence

| Requirement | Status | Evidence / next action |
|---|---|---|
| Ollama local inference | Implemented; live runtime unverified | `backend/app/local_ai.py`; test on target laptop |
| No paid/cloud LLM fallback | Implemented in multi-product app | Sole loopback Ollama adapter; offline network proof still required |
| SQLite | Implemented | businesses/products/prospects/generated/research/embeddings/logs/ai_tasks |
| Python + FastAPI | Implemented | `backend/app/main.py` |
| React dashboard | Source committed; production build unverified | `frontend/src/main.jsx`; npm install/build remains outstanding |
| Multi-product configuration | Implemented | businesses/products records and CRUD routes |
| Product-specific ICP | Implemented in code | `POST /api/ai/icp/{product_id}` |
| Prospect import | Implemented | CSV and manual form |
| Public website research | Partial | App fetches one supplied public URL; first-time research is online-only |
| Scrapy/Playwright research helpers | Implemented as separate preload scripts | robots-aware Scrapy; same-host Playwright helper |
| Buying-signal classification | Implemented in code | `POST /api/ai/signals/{prospect_id}` |
| Problem-statement generation | Implemented in code | `POST /api/ai/problem/{prospect_id}` |
| Prospect scoring | Implemented in code; model-output QA pending | `POST /api/ai/score/{prospect_id}` |
| Personalised email generation | Implemented, draft-only | `POST /api/ai/email/{prospect_id}`; no sending |
| Reply classification | Implemented in code | `POST /api/ai/reply` |
| Local embeddings and semantic retrieval | Implemented in code; requires model download | `download_embedding_model.py`, embeddings routes |
| Hardware detection | Implemented, heuristic | `GET /api/hardware` |
| Local execution logs | Implemented | `GET /api/logs` includes event/model/status/duration |
| Ollama failure handling | Implemented | HTTP 503, no fallback |
| Task queue/retry | Implemented as local SQLite/manual retry | `GET /api/tasks`, `POST /api/tasks/{id}/retry`; no automatic worker |
| Offline acceptance | Not yet executed on target laptop | Follow `OFFLINE_ACCEPTANCE.md` and capture actual evidence |
| Backend tests | Four smoke tests pass in prepared workspace, including queue/no-fallback coverage | Live Ollama inference remains unverified |
| Frontend build | Not verified | npm install timed out in build environment |
| Deployment | Not implemented | Local setup is delivery target |
| Screen recording | Not recorded | Follow `DEMO_SCRIPT.md` |

## Interpreting status

“Implemented in code” means the route/module is present; it is not equivalent to a demonstrated successful live model run. Only mark offline acceptance as passed after disconnecting Wi-Fi/Ethernet on the target computer and successfully repeating every local AI workflow with pre-downloaded models and persisted prospect research.


## Latest prepared-workspace checks

- Backend smoke suite: 4 passed, including no-cloud-fallback and manual queued-task retry.
- Python backend syntax compilation: passed.
- React JSX syntax transpile check: passed.
- Npm dependency installation and production build: not verified because required packages were not cached in the build environment.
- Live Qwen3 inference and disconnected-network acceptance: not yet performed on the target laptop.
