# Offline acceptance checklist

## Online preparation

- [ ] Install Ollama and run `ollama pull qwen3:0.6b`.
- [ ] Verify the exact tag with `ollama list`; keep `OLLAMA_MODEL=qwen3:0.6b`.
- [ ] In `backend/`, install Python packages from `requirements.txt`.
- [ ] Run `python download_embedding_model.py` to cache all-MiniLM-L6-v2 locally.
- [ ] Install Playwright browser binaries with `playwright install chromium` if using that preloader.
- [ ] In `frontend/`, run `npm install`; verify `npm run build`.
- [ ] Create one business, at least two products and at least two prospects.
- [ ] Store public website research text for each prospect or import source evidence text.
- [ ] Verify `GET /api/health` shows Ollama available and the model installed.
- [ ] Start Ollama, FastAPI and Vite on localhost.

## Disconnected-network test

- [ ] Disconnect Wi-Fi and Ethernet. Do not just close the browser.
- [ ] Keep Ollama, FastAPI and Vite running.
- [ ] Run `python offline_acceptance.py` from `backend/`.
- [ ] Confirm business profile generation completes.
- [ ] Confirm product-specific ICP generation completes for each product.
- [ ] Confirm stored research returns `stored_offline` without website access.
- [ ] Confirm buying-signal classification completes.
- [ ] Confirm problem-statement generation completes.
- [ ] Confirm prospect scoring completes; inspect reasons and missing data.
- [ ] Confirm personalised email drafts generate.
- [ ] Confirm reply classification completes.
- [ ] Confirm local embedding indexing and semantic search complete.
- [ ] Capture terminal output and dashboard execution logs.

## Ollama-unavailable test

- [ ] Stop Ollama while leaving FastAPI running.
- [ ] Trigger a generation workflow.
- [ ] Confirm HTTP 503 and a task ID in the error message.
- [ ] Open Queued AI Tasks in the dashboard; confirm a queued item exists.
- [ ] Confirm an unavailable model-execution log exists.
- [ ] Confirm no cloud provider/network request was attempted.
- [ ] Restart Ollama and use the manual retry action. Inspect the task result.
- [ ] Rerun the original workflow to persist its output in its normal business/prospect record.

## Pass criteria

Do not call this test passed until performed on the actual submission laptop with internet disabled after model/dependency downloads. A mocked unit test or source-code inspection is not a substitute.
