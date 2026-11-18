# Implementation status and acceptance evidence

Last updated: 18 November 2026. Status distinguishes source-code presence from behaviour actually demonstrated on the target Windows laptop.

| Requirement | Current status | Evidence / remaining action |
|---|---|---|
| Ollama local inference | **Verified on target laptop** | Qwen3 0.6B loaded locally; direct Ollama generation returned a response |
| No paid/cloud LLM fallback | **Implemented; offline network proof pending** | Sole loopback Ollama adapter, remote endpoints and cloud tags blocked; capture disconnected-network evidence |
| FastAPI backend | **Live API verified** | `/api/health` returned `ok: true`, Ollama available and Qwen3 ready on port 8010 |
| SQLite business and products | **Verified on target laptop** | Northstar Technologies and two products created and read back via API |
| AI business profile | **Live generation observed** | Qwen3 business-profile request completed and success logged at 341,733 ms (~5m 42s); final profile read-back from SQLite still needs confirmation |
| Product-specific ICP | Implemented in code; **not yet live-verified** | `POST /api/ai/icp/{product_id}`; generate and inspect a distinct ICP for each product |
| Prospect import | Implemented in code; not yet live-verified | Import sample CSV and verify prospect records |
| Public website research | Partial | App fetches a supplied public URL; first-time retrieval requires internet; confirm content is persisted |
| Buying-signal classification | Implemented in code; not yet live-verified | `POST /api/ai/signals/{prospect_id}`; inspect evidence and avoid unsupported signals |
| Problem-statement generation | Implemented in code; not yet live-verified | `POST /api/ai/problem/{prospect_id}` |
| Prospect scoring | Implemented in code; not yet live-verified | `POST /api/ai/score/{prospect_id}`; inspect score rationale and JSON quality |
| Personalised email generation | **Live generated for both synthetic demo prospects; formatting needs refinement** | `POST /api/ai/email/{prospect_id}` returned product-specific text for AppointmentPro and CustomerFlow CRM. Output appended product metadata after the body, so clean email formatting still needs refinement; draft only, no sending |
| Reply classification | **Live verified on synthetic demo reply** | `POST /api/ai/reply` returned category `interested`, sentiment `positive`, rationale, and suggested next step using Qwen3 0.6B |
| Local embeddings and semantic retrieval | Implemented in code; **not installed/tested on target laptop** | Cache all-MiniLM-L6-v2 locally, index a prospect and run semantic search |
| Hardware detection | Verified in health response | Target machine reported 3.9 GB RAM, 2 CPU cores and no detected GPU; recommendation is heuristic |
| Local execution logs | **Verified for business-profile event** | `GET /api/logs` showed `business_profile`, `qwen3:0.6b`, `success`, 341,733 ms and local loopback detail |
| Ollama failure handling | Partially observed | HTTP 503 occurred and queued requests were preserved when Ollama was unavailable; repeat a controlled stop/restart test |
| Task queue/retry | Implemented in code; end-to-end retry **not yet passed** | SQLite queue and manual retry routes exist; complete successful retry after Ollama restart |
| React dashboard | Source committed; **not run on target laptop** | Install npm dependencies, start Vite, verify port 8010 API connectivity and key workflows |
| Backend tests | Four smoke tests passed in prepared workspace | Re-run on target laptop if practical; prepared-workspace result is not target-machine acceptance |
| Frontend production build | Not verified | Run `npm install` and `npm run build` in frontend |
| Offline acceptance | **Not performed** | Disconnect Wi-Fi/Ethernet and complete every workflow using pre-downloaded dependencies, model weights and stored prospect evidence |
| Deployment | Not implemented | Local setup is an allowed delivery path in the assignment |
| Screen recording | Not recorded | Record a 5–10 minute honest demonstration after tests |

## Target-machine observations

- Windows computer: Intel Celeron N3060, 2 CPU cores, 3.9 GB installed RAM, Intel HD Graphics, no discrete GPU detected.
- C: drive initially had less than 1 GB free; E: was used for project and Ollama model storage.
- Ollama model: `qwen3:0.6b` (Apache-2.0 model family; verify the exact pulled model tag's current card at release).
- Local model directory: `E:\\Ollama\\models`.
- FastAPI port: `8010` because port 8000 returned a different server's 404 page / was not suitable for this application.
- A fresh Qwen3 prompt with thinking disabled, 1,024 context and 32 output tokens returned `OK.`
- A business-profile call through FastAPI produced text and a success log with a duration of 341,733 ms (~5m 42s). This is very slow and may make the complete offline test impractical on this hardware without reducing workload/prompt sizes.

## Prepared-workspace checks

- Backend smoke suite: 4 passed, including no-cloud-fallback and manual queued-task retry coverage.
- Python backend syntax compilation: passed.
- React JSX syntax transpile check: passed.
- Npm dependency installation and production build: not verified.
- Live target-machine inference: partially verified as detailed above.
- Disconnected-network acceptance: not performed.

## Port and low-memory runtime alignment

The target laptop runs FastAPI on localhost port 8010 because port 8000 is occupied by another process/application. The React dashboard defaults to `http://127.0.0.1:8010/api` (overridable with `VITE_API_BASE`). The offline acceptance script defaults to the same port (overridable with `HARVEY_API_BASE`) and uses a longer HTTP timeout for slow CPU-only inference.

## Acceptance rule

“Implemented in code” is not equivalent to a demonstrated successful workflow. Do not claim the project is fully accepted or offline-tested until the actual submission laptop has completed all required generation workflows with Wi-Fi/Ethernet disconnected after downloading all dependencies and model files. Do not present the four prepared-workspace unit/smoke tests as a substitute for the offline acceptance test.


## Additional live workflow evidence — 18 November 2026

- Stored research was read back for two synthetic prospects: Demo Dental Group (372 characters) and Demo Home Services (396 characters).
- Buying-signal classification ran for both. The outputs explicitly caveated that the evidence was synthetic and not independently verified.
- Prospect scoring ran for both and returned score 0 because evidence was synthetic/unverifiable. Do not represent these scores as real lead qualification.
- Personalised email endpoint returned text for both prospects and referenced their respective products. Output formatting was imperfect because product metadata appeared after the draft body; refine before presenting as polished outreach.
- Reply classification ran on a synthetic appointment-scheduling enquiry and returned category `interested`, sentiment `positive`, rationale, and a suggested follow-up.
- These records are synthetic acceptance/demo data, not real prospect research.
