"""Run after collecting prospect evidence and downloading both local models.
Run with internet DISCONNECTED and the three local services already started.
"""
from __future__ import annotations
import sys
import httpx

BASE = "http://127.0.0.1:8000/api"
SAMPLE_REPLY = "Thanks for reaching out. We already have a solution, but could you send details about pricing and integrations?"

def call(client, method, path, **kwargs):
    r = client.request(method, BASE + path, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> HTTP {r.status_code}: {r.text}")
    return r.json()

def main():
    with httpx.Client(timeout=240) as client:
        health = call(client, "GET", "/health")
        inference = health["inference"]
        if not inference.get("available") or not inference.get("model_installed"):
            raise RuntimeError(f"Ollama/local model not ready: {inference}")
        businesses = call(client, "GET", "/businesses")
        products = call(client, "GET", "/products")
        prospects = call(client, "GET", "/prospects")
        if not businesses or not products or not prospects:
            raise RuntimeError("Create at least one business, product, and prospect before the offline test.")
        print(f"LOCAL MODEL: {inference['model']} at {inference['url']}")
        for b in businesses:
            print("business profile:", b["name"])
            call(client, "POST", f"/ai/business-profile/{b['id']}")
        for p in products:
            print("product ICP:", p["name"])
            call(client, "POST", f"/ai/icp/{p['id']}")
        completed = 0
        for p in prospects:
            if not p.get("product_id"):
                print("SKIP prospect without product:", p["company"])
                continue
            print("prospect workflow:", p["company"])
            research = call(client, "POST", f"/research/{p['id']}")
            if not research.get("research", "").strip():
                raise RuntimeError(f"No stored research/source text for {p['company']}")
            call(client, "POST", f"/embeddings/index/{p['id']}")
            call(client, "POST", f"/ai/signals/{p['id']}")
            call(client, "POST", f"/ai/problem/{p['id']}")
            score = call(client, "POST", f"/ai/score/{p['id']}")
            call(client, "POST", f"/ai/email/{p['id']}")
            call(client, "POST", "/ai/reply", json={"prospect_id": p["id"], "reply": SAMPLE_REPLY})
            completed += 1
            print(f"  lead score returned: {score.get('score')} (inspect model result and rationale)")
        semantic = call(client, "POST", "/embeddings/search", json={"query": "companies with a hiring trigger and manual appointment booking", "limit": 5})
        print(f"semantic retrieval: {len(semantic['results'])} local matches")
        logs = call(client, "GET", "/logs")
        success = [x for x in logs if x["status"] == "success"]
        print(f"PASS: business profiles, product ICPs, {completed} prospect pipelines, semantic retrieval; {len(success)} successful logged executions.")
        print("Save a screenshot of the Execution Logs page and this terminal output as test evidence.")

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
