from __future__ import annotations
import csv, io, json, time, ipaddress, socket
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import httpx
from .db import init_db, connect, rows, one
from .local_ai import generate, ollama_status, LocalModelUnavailable, log_event, DEFAULT_MODEL
from .hardware import report

app = FastAPI(title="Harvey Local AI Sales Agent", version="1.0.0", description="Local-only multi-product sales intelligence using Ollama + SQLite.")
@app.middleware("http")
async def ensure_database(request: Request, call_next):
    init_db()
    return await call_next(request)

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
class BusinessIn(BaseModel):
 name: str = Field(min_length=1); description: str = ""; website: str = ""; industry: str = ""
class ProductIn(BaseModel):
 business_id: int; name: str = Field(min_length=1); description: str = Field(min_length=1); benefits: str = ""; target_market: str = ""
class ProspectIn(BaseModel):
 product_id: int | None = None; company: str = Field(min_length=1); website: str = ""; industry: str = ""; company_size: str = ""; contact_name: str = ""; title: str = ""; email: str = ""; location: str = ""; source_text: str = ""
class GenerateIn(BaseModel): product_id: int | None = None
class ReplyIn(BaseModel): prospect_id: int; reply: str = Field(min_length=1)
class SemanticSearchIn(BaseModel): query: str = Field(min_length=2); product_id: int | None = None; limit: int = Field(default=5, ge=1, le=20)

@app.get("/api/health")
async def health():
    return {"ok": True, "app": "Harvey Local AI Sales Agent", "inference": await ollama_status(), "hardware": report()}
@app.get("/api/hardware")
def hardware(): return report()
@app.get("/api/businesses")
def businesses(): return rows("SELECT * FROM businesses ORDER BY id DESC")
@app.post("/api/businesses")
def add_business(item: BusinessIn):
    with connect() as db:
        cur=db.execute("INSERT INTO businesses(name,description,website,industry) VALUES(?,?,?,?)",(item.name,item.description,item.website,item.industry)); ident=cur.lastrowid
    return one("SELECT * FROM businesses WHERE id=?",(ident,))
@app.get("/api/products")
def products(): return rows("SELECT p.*,b.name business_name FROM products p JOIN businesses b ON b.id=p.business_id ORDER BY p.id DESC")
@app.post("/api/products")
def add_product(item: ProductIn):
    if not one("SELECT id FROM businesses WHERE id=?",(item.business_id,)): raise HTTPException(404,"Business not found")
    with connect() as db:
        cur=db.execute("INSERT INTO products(business_id,name,description,benefits,target_market) VALUES(?,?,?,?,?)",(item.business_id,item.name,item.description,item.benefits,item.target_market)); ident=cur.lastrowid
    return one("SELECT * FROM products WHERE id=?",(ident,))
@app.get("/api/prospects")
def prospects(product_id: int|None=None):
    if product_id: return rows("SELECT * FROM prospects WHERE product_id=? ORDER BY score DESC,id DESC",(product_id,))
    return rows("SELECT * FROM prospects ORDER BY score DESC,id DESC")
@app.post("/api/prospects")
def add_prospect(item: ProspectIn):
    if item.product_id and not one("SELECT id FROM products WHERE id=?",(item.product_id,)): raise HTTPException(404,"Product not found")
    with connect() as db:
        cur=db.execute("INSERT INTO prospects(product_id,company,website,industry,company_size,contact_name,title,email,location,source_text) VALUES(?,?,?,?,?,?,?,?,?,?)",tuple(item.model_dump().values())); ident=cur.lastrowid
    return one("SELECT * FROM prospects WHERE id=?",(ident,))
@app.post("/api/prospects/import")
async def import_csv(file: UploadFile=File(...), product_id: int|None=None):
    if not file.filename.lower().endswith(".csv"): raise HTTPException(400,"Upload a CSV file")
    raw=(await file.read()).decode("utf-8-sig")
    reader=csv.DictReader(io.StringIO(raw)); count=0
    for r in reader:
        company=(r.get("company") or r.get("Company") or r.get("name") or "").strip()
        if not company: continue
        item=ProspectIn(product_id=product_id,company=company,website=r.get("website",r.get("Website","")),industry=r.get("industry",r.get("Industry","")),company_size=r.get("company_size",""),contact_name=r.get("contact_name",r.get("Contact Name","")),title=r.get("title",r.get("Title","")),email=r.get("email",r.get("Email","")),location=r.get("location",""),source_text=r.get("source_text",""))
        add_prospect(item); count+=1
    return {"imported":count}

async def require_product(product_id: int):
    p=one("SELECT p.*,b.name company_name,b.description company_description,b.website company_website,b.industry company_industry FROM products p JOIN businesses b ON b.id=p.business_id WHERE p.id=?",(product_id,))
    if not p: raise HTTPException(404,"Product not found")
    return p
async def require_prospect(prospect_id: int):
    p=one("SELECT * FROM prospects WHERE id=?",(prospect_id,))
    if not p: raise HTTPException(404,"Prospect not found")
    return p
async def ai(prompt: str, event: str):
    try:
        return await generate(prompt, event)
    except LocalModelUnavailable as exc:
        # Preserve the exact prompt locally so the user can retry after
        # starting Ollama. No background or remote worker is started.
        with connect() as db:
            cur = db.execute(
                "INSERT INTO ai_tasks(event,prompt,status,last_error) VALUES(?,?,?,?)",
                (event, prompt, "queued", str(exc)[:2000]),
            )
            task_id = cur.lastrowid
        raise HTTPException(
            503,
            f"{exc} The task is safely queued in local SQLite as task #{task_id}. "
            "Start Ollama and retry it from GET /api/tasks.",
        )

@app.post("/api/ai/business-profile/{business_id}")
async def business_profile(business_id: int):
    b=one("SELECT * FROM businesses WHERE id=?",(business_id,))
    if not b: raise HTTPException(404,"Business not found")
    result=await ai(f"Create a concise, evidence-grounded company profile. Separate known facts from assumptions.\nCompany: {json.dumps(b)}\nReturn sections: overview, value proposition, differentiators, missing information.","business_profile")
    with connect() as db: db.execute("UPDATE businesses SET profile=? WHERE id=?",(result,business_id))
    return {"result":result,"model":DEFAULT_MODEL,"mode":"local"}
@app.post("/api/ai/icp/{product_id}")
async def generate_icp(product_id: int):
    p=await require_product(product_id)
    result=await ai(f"Generate a precise B2B ideal customer profile for this product. Include firmographics, buyer roles, pains, triggers, disqualifiers and evidence signals. Avoid unsupported claims.\n{json.dumps(p)}","icp_generation")
    with connect() as db: db.execute("UPDATE products SET icp=? WHERE id=?",(result,product_id))
    return {"result":result,"model":DEFAULT_MODEL,"mode":"local"}
@app.post("/api/research/{prospect_id}")
async def research(prospect_id: int):
    p=await require_prospect(prospect_id)
    # Reuse research already downloaded and stored. This is the offline path.
    if p["research"]:
        return {"prospect_id":prospect_id,"research":p["research"],"source":"stored_offline"}
    text=p["source_text"]
    source="stored"
    # Imported evidence is already local; do not make an online request if it exists.
    if p["website"] and not text.strip():
        source="website"
        parsed = urlparse(p["website"])
        host = (parsed.hostname or "").lower()
        is_public_host = bool(host) and parsed.scheme in {"http", "https"} and not parsed.username and not parsed.password
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".localhost")):
            is_public_host = False
        try:
            ip = ipaddress.ip_address(host)
            is_public_host = is_public_host and ip.is_global
        except ValueError:
            pass
        if is_public_host and not host.endswith((".localhost", ".local", ".internal")):
            try:
                resolved = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))}
                is_public_host = bool(resolved) and all(ipaddress.ip_address(address).is_global for address in resolved)
            except (OSError, ValueError):
                is_public_host = False
        else:
            is_public_host = False
        if not is_public_host:
            raise HTTPException(400, "Research accepts public HTTP(S) websites only; local/private hosts are blocked.")
        try:
            # Redirects are deliberately not followed so a public page cannot
            # redirect this local agent to a private network address.
            async with httpx.AsyncClient(timeout=12, follow_redirects=False, trust_env=False,
                                         headers={"User-Agent":"HarveyLocalResearch/1.0"}) as client:
                response = await client.get(p["website"])
                if 300 <= response.status_code < 400:
                    raise HTTPException(400, "Website redirected. Enter its final public URL directly.")
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                for tag in soup(["script", "style", "noscript"]): tag.decompose()
                downloaded = " ".join(soup.stripped_strings)[:12000]
                text = (text + "\n" + downloaded).strip()
        except httpx.HTTPError as exc:
            log_event("web_research", "partial", 0, str(exc));
    if not text: raise HTTPException(400,"No stored research text. Provide source_text or research this site while online.")
    with connect() as db: db.execute("UPDATE prospects SET research=? WHERE id=?",(text,prospect_id))
    return {"prospect_id":prospect_id,"research":text,"source":source}
@app.post("/api/ai/signals/{prospect_id}")
async def classify_signals(prospect_id: int):
    p=await require_prospect(prospect_id)
    context=p["research"] or p["source_text"]
    if not context: raise HTTPException(400,"Research this prospect or import source_text first")
    result=await ai(f"Classify buying signals from this evidence. Return JSON array with signal, evidence_quote, confidence (0-1), and caveat. Never invent signals.\nProduct: {p['product_id']}\nCompany: {p['company']}\nEvidence:\n{context}","buying_signal_classification")
    try: json.loads(result)
    except ValueError: pass
    with connect() as db: db.execute("UPDATE prospects SET buying_signals=? WHERE id=?",(result,prospect_id))
    return {"result":result,"model":DEFAULT_MODEL}
@app.post("/api/ai/problem/{prospect_id}")
async def problem_statement(prospect_id: int):
    p=await require_prospect(prospect_id); product=await require_product(p["product_id"]) if p["product_id"] else None
    result=await ai(f"Write a prospect-specific problem statement. Anchor every factual claim in supplied evidence; label hypotheses. Product: {json.dumps(product)}\nProspect: {json.dumps(p)}","problem_statement")
    with connect() as db: db.execute("UPDATE prospects SET problem_statement=? WHERE id=?",(result,prospect_id))
    return {"result":result,"model":DEFAULT_MODEL}
@app.post("/api/ai/score/{prospect_id}")
async def score_prospect(prospect_id: int):
    p=await require_prospect(prospect_id)
    result=await ai(f"Score this B2B prospect from 0-100 for the configured product. Weigh ICP fit, buying intent, problem evidence, reachability, and data confidence. Return JSON {{score, reasons, missing_data}}. Do not assume a high score without evidence.\n{json.dumps(p)}","prospect_scoring")
    try:
        parsed=json.loads(result); score=max(0,min(100,int(parsed.get("score",0)))); reason=json.dumps(parsed.get("reasons",[]))
        with connect() as db: db.execute("UPDATE prospects SET score=?,score_reason=? WHERE id=?",(score,reason,prospect_id))
    except (ValueError,TypeError,AttributeError): score=0
    return {"result":result,"score":score,"model":DEFAULT_MODEL}
@app.post("/api/ai/email/{prospect_id}")
async def email(prospect_id: int):
    p=await require_prospect(prospect_id); product=await require_product(p["product_id"]) if p["product_id"] else None
    result=await ai(f"Draft a concise, truthful, personalised B2B first-touch email. Use only supported facts; do not invent a relationship, metrics or trigger. Include subject and body.\nProduct: {json.dumps(product)}\nProspect: {json.dumps(p)}","personalised_email")
    with connect() as db: db.execute("INSERT INTO generated(prospect_id,kind,content) VALUES(?,?,?)",(prospect_id,"email",result))
    return {"result":result,"model":DEFAULT_MODEL}
@app.post("/api/ai/reply")
async def classify_reply(item: ReplyIn):
    p=await require_prospect(item.prospect_id)
    result=await ai(f"Classify this sales reply. Return JSON with category (interested|objection|not_interested|unsubscribe|out_of_office|follow_up|unclear), sentiment, rationale and suggested_next_step. Treat opt-out requests conservatively. Company: {p['company']}\nReply:\n{item.reply}","reply_classification")
    with connect() as db: db.execute("INSERT INTO generated(prospect_id,kind,content) VALUES(?,?,?)",(item.prospect_id,"reply_classification",result))
    return {"result":result,"model":DEFAULT_MODEL}

@app.post("/api/embeddings/index/{prospect_id}")
def index_prospect_embedding(prospect_id: int):
    p=one("SELECT * FROM prospects WHERE id=?",(prospect_id,))
    if not p: raise HTTPException(404,"Prospect not found")
    text=(p["research"] or p["source_text"] or "").strip()
    if not text: raise HTTPException(400,"No local research evidence to embed")
    from .embeddings import encode as encode_embedding, MODEL_NAME, EmbeddingUnavailable
    try: vector=encode_embedding(text)
    except EmbeddingUnavailable as exc: raise HTTPException(503,str(exc))
    with connect() as db:
        db.execute("INSERT INTO prospect_embeddings(prospect_id,model,vector) VALUES(?,?,?) ON CONFLICT(prospect_id) DO UPDATE SET model=excluded.model,vector=excluded.vector,created_at=CURRENT_TIMESTAMP",(prospect_id,MODEL_NAME,vector.tobytes()))
    return {"prospect_id":prospect_id,"model":MODEL_NAME,"dimensions":int(vector.shape[0]),"stored_locally":True}

@app.post("/api/embeddings/search")
def semantic_search(item: SemanticSearchIn):
    import numpy as np
    from .embeddings import encode as encode_embedding, MODEL_NAME, EmbeddingUnavailable
    try: query=encode_embedding(item.query)
    except EmbeddingUnavailable as exc: raise HTTPException(503,str(exc))
    sql="SELECT p.*,e.model,e.vector FROM prospect_embeddings e JOIN prospects p ON p.id=e.prospect_id"
    args=()
    if item.product_id:
        sql+=" WHERE p.product_id=?"; args=(item.product_id,)
    matches=[]
    for row in rows(sql,args):
        vector=np.frombuffer(row.pop("vector"),dtype=np.float32)
        if vector.shape == query.shape:
            matches.append((float(np.dot(query,vector)),row))
    matches.sort(key=lambda x:x[0],reverse=True)
    return {"query":item.query,"model":MODEL_NAME,"results":[{"similarity":round(score,4),"prospect":prospect} for score,prospect in matches[:item.limit]]}

@app.get("/api/tasks")
def queued_tasks():
    """List locally queued AI requests and their retry results."""
    return rows("SELECT id,event,status,attempts,last_error,result,created_at,updated_at FROM ai_tasks ORDER BY id DESC LIMIT 100")

@app.post("/api/tasks/{task_id}/retry")
async def retry_queued_task(task_id: int):
    """Manually retry one stored task once local Ollama is back online."""
    task = one("SELECT * FROM ai_tasks WHERE id=?", (task_id,))
    if not task:
        raise HTTPException(404, "Queued task not found")
    if task["status"] == "completed":
        return {"task_id": task_id, "status": "completed", "result": task["result"]}
    with connect() as db:
        db.execute(
            "UPDATE ai_tasks SET status='running', attempts=attempts+1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (task_id,),
        )
    try:
        result = await generate(task["prompt"], task["event"])
    except LocalModelUnavailable as exc:
        with connect() as db:
            db.execute(
                "UPDATE ai_tasks SET status='queued', last_error=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (str(exc)[:2000], task_id),
            )
        raise HTTPException(503, f"Local model is still unavailable. Task #{task_id} remains queued.")
    with connect() as db:
        db.execute(
            "UPDATE ai_tasks SET status='completed', result=?, last_error='', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (result, task_id),
        )
    return {"task_id": task_id, "status": "completed", "result": result}

@app.get("/api/logs")
def logs(): return rows("SELECT * FROM logs ORDER BY id DESC LIMIT 100")
