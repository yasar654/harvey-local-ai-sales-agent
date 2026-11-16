# 5–10 minute demonstration plan

Use fictional companies and contacts only.

## 0:00–0:50 — Local architecture
Show the Overview dashboard, Ollama model status, RAM/CPU/GPU report and zero-cloud status. Open `backend/app/local_ai.py` and explain its loopback-only Ollama endpoint and no-fallback behaviour.

## 0:50–1:50 — Business and products
Create a business profile. Generate its AI business profile. Add at least two products and generate a separate ICP for each product.

## 1:50–2:40 — Prospect discovery and research
Import `backend/sample_prospects.csv` or add 2–3 fictional prospects. Explain that public research must be collected before going offline. Collect/store website evidence or import supplied source text.

## 2:40–4:40 — Prospect qualification
Select one prospect and run buying-signal classification, problem statement, scoring and local embedding indexing/search. Inspect the evidence, signal quote, score reasoning and caveats. Explain that model-generated claims require human verification.

## 4:40–5:45 — Outreach and replies
Generate a personalised email draft. State clearly that the app does not send email. Submit a sample conversation and classify the reply.

## 5:45–6:45 — Logs and failure handling
Show the local model name, event, duration and result in Execution Logs. Stop Ollama and trigger a generation. Show the HTTP 503 and the queued item in Queued AI Tasks. Restart Ollama and retry the task.

## 6:45–8:45 — Offline acceptance
Before recording, download models/dependencies, store prospect evidence and start all local services. Disconnect Wi-Fi/Ethernet. Run `python offline_acceptance.py` from backend. Show the local workflow completing and corresponding dashboard logs.

## Closing
Report honestly that first-time web research requires internet, generation/email actions rely on local Ollama, the task queue is manually retried, and no email is sent. Do not present an unexecuted offline test or unbuilt frontend as passed.
