import os
import sqlite3
import uuid
import requests
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_system import build_workflow, init_db, DB_PATH

app = FastAPI(title="LangGraph ERP Invoice Audit Dashboard")

# Compile LangGraph
compiled_graph = build_workflow()

# LLM configurations stored in memory
llm_config = {
    "LLM_MODE": os.environ.get("LLM_MODE", "ollama"), # Default to Ollama now
    "OLLAMA_URL": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
    "OLLAMA_MODEL": os.environ.get("OLLAMA_MODEL", "llama3.1"),
    "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    "GEMINI_MODEL": os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
}

# Ensure DB is initialized
if not os.path.exists(DB_PATH):
    init_db()

# Models for API
class InvoiceRequest(BaseModel):
    invoice_id: str
    po_id: str
    supplier_name: str
    item_id: str
    quantity: int
    unit_price: float
    total_amount: float

class ApprovalRequest(BaseModel):
    thread_id: str
    decision: str  # APPROVED or REJECTED

class ConfigRequest(BaseModel):
    mode: str
    ollama_url: str
    ollama_model: str
    openai_key: str = ""
    gemini_key: str = ""


# Sync memory configuration to environment variables
def apply_config():
    os.environ["LLM_MODE"] = llm_config["LLM_MODE"]
    os.environ["OLLAMA_URL"] = llm_config["OLLAMA_URL"]
    os.environ["OLLAMA_MODEL"] = llm_config["OLLAMA_MODEL"]
    os.environ["OPENAI_MODEL"] = llm_config["OPENAI_MODEL"]
    os.environ["GEMINI_MODEL"] = llm_config["GEMINI_MODEL"]

# Apply initial environment
apply_config()


# Helper to format state response
def get_graph_state_response(thread_id: str, state_value: Dict[str, Any]) -> Dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    next_steps = compiled_graph.get_state(config).next
    
    return {
        "thread_id": thread_id,
        "is_interrupted": len(next_steps) > 0 and "manager_approval_node" in next_steps,
        "next_nodes": list(next_steps),
        "invoice_parsed": state_value.get("invoice_parsed", {}),
        "po_data": state_value.get("po_data"),
        "gr_data": state_value.get("gr_data"),
        "reconciliation_status": state_value.get("reconciliation_status", "PENDING"),
        "discrepancy_amount": state_value.get("discrepancy_amount", 0.0),
        "supplier_email_draft": state_value.get("supplier_email_draft"),
        "post_status": state_value.get("post_status", "PENDING"),
        "human_decision": state_value.get("human_decision"),
        "logs": state_value.get("logs", [])
    }


# =====================================================================
# REST ENDPOINTS
# =====================================================================

@app.get("/api/health")
def check_llm_health():
    """Checks connection health of the active LLM configuration."""
    mode = llm_config["LLM_MODE"]
    
    if mode == "ollama":
        url = llm_config["OLLAMA_URL"]
        model = llm_config["OLLAMA_MODEL"]
        try:
            # Ping the local Ollama instance tags endpoint
            res = requests.get(f"{url}/api/tags", timeout=1.5)
            if res.status_code == 200:
                # Check if the pulled models list includes our model
                models_data = res.json()
                models = [m["name"] for m in models_data.get("models", [])]
                model_found = any(model in m for m in models)
                
                if model_found:
                    return {"status": "connected", "details": f"Ollama '{model}' loaded."}
                else:
                    available = ", ".join(models) if models else "None"
                    return {"status": "warning", "details": f"Ollama online, but model '{model}' not pulled. Available: {available}"}
            return {"status": "disconnected", "details": f"Ollama server returned code {res.status_code}."}
        except Exception:
            return {"status": "disconnected", "details": f"Ollama offline on {url}"}
            
    elif mode == "openai":
        has_key = bool(os.environ.get("OPENAI_API_KEY"))
        if has_key:
            return {"status": "connected", "details": f"OpenAI ({llm_config['OPENAI_MODEL']}) ready."}
        return {"status": "disconnected", "details": "OpenAI API Key is missing."}
        
    elif mode == "gemini":
        has_key = bool(os.environ.get("GEMINI_API_KEY"))
        if has_key:
            return {"status": "connected", "details": f"Gemini ({llm_config['GEMINI_MODEL']}) ready."}
        return {"status": "disconnected", "details": "Gemini API Key is missing."}
        
    else:
        return {"status": "connected", "details": "Simulator Mode active."}


@app.get("/api/config")
def get_config():
    """Returns the current LLM routing configurations."""
    return {
        "mode": llm_config["LLM_MODE"],
        "ollama_url": llm_config["OLLAMA_URL"],
        "ollama_model": llm_config["OLLAMA_MODEL"],
        "openai_key_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "gemini_key_configured": bool(os.environ.get("GEMINI_API_KEY"))
    }


@app.post("/api/config")
def set_config(req: ConfigRequest):
    """Updates the LLM configuration dynamically."""
    llm_config["LLM_MODE"] = req.mode
    llm_config["OLLAMA_URL"] = req.ollama_url
    llm_config["OLLAMA_MODEL"] = req.ollama_model
    
    if req.openai_key.strip():
        os.environ["OPENAI_API_KEY"] = req.openai_key.strip()
    if req.gemini_key.strip():
        os.environ["GEMINI_API_KEY"] = req.gemini_key.strip()
        
    apply_config()
    return {"status": "success", "message": "Configuration updated successfully."}


@app.post("/api/invoice")
def process_invoice(invoice: InvoiceRequest):
    """Submits a new invoice and runs the LangGraph workflow."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Read health status to log warnings if offline
    health = check_llm_health()
    
    initial_state = {
        "messages": [],
        "invoice_raw": invoice.dict(),
        "invoice_parsed": {},
        "po_data": None,
        "gr_data": None,
        "reconciliation_status": "PENDING",
        "discrepancy_amount": 0.0,
        "supplier_email_draft": None,
        "post_status": "PENDING",
        "human_decision": None,
        "logs": [f"System Audit: Started. Target model backend state: {health['status'].upper()} ({health['details']})"]
    }
    
    if health["status"] == "disconnected":
        initial_state["logs"].append("System warning: Target LLM model is offline. Auditing will execute using pre-compiled rules.")
    
    try:
        state = compiled_graph.invoke(initial_state, config=config)
        return get_graph_state_response(thread_id, state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approve")
def approve_invoice(req: ApprovalRequest):
    """Resumes an interrupted invoice thread with manager decision."""
    config = {"configurable": {"thread_id": req.thread_id}}
    
    current_state = compiled_graph.get_state(config)
    if not current_state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")
        
    next_steps = current_state.next
    if "manager_approval_node" not in next_steps:
        raise HTTPException(status_code=400, detail="Workflow is not currently awaiting manager approval.")
        
    try:
        decision = req.decision.upper() # APPROVED or REJECTED
        logs = current_state.values.get("logs", []).copy()
        logs.append(f"Manager Portal: Manager manual action performed: {decision}")
        
        compiled_graph.update_state(
            config, 
            {"human_decision": decision, "logs": logs}, 
            as_node="manager_approval_node"
        )
        
        state = compiled_graph.invoke(None, config=config)
        return get_graph_state_response(req.thread_id, state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/db")
def get_db_state():
    """Returns the current state of tables in SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM purchase_orders")
    pos = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM goods_receipts")
    grs = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM invoices ORDER BY post_date DESC")
    invoices = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "purchase_orders": pos,
        "goods_receipts": grs,
        "invoices": invoices
    }


@app.post("/api/reset-db")
def reset_db():
    """Resets the mock ERP database to initial seed values."""
    init_db()
    return {"status": "success", "message": "ERP Database reset to seed values."}


# Serve dashboard index
@app.get("/")
def get_index():
    index_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("index.html not found. Place it in the app directory.")

@app.get("/styles.css")
def get_css():
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.css")
    return FileResponse(css_path)

@app.get("/app.js")
def get_js():
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.js")
    return FileResponse(js_path)

if __name__ == "__main__":
    import uvicorn
    # Start on port 8001, listening on all interfaces inside container
    uvicorn.run(app, host="0.0.0.0", port=8001)
