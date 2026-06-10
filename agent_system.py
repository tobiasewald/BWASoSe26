import os
import sqlite3
from typing import List, Optional, TypedDict, Dict, Any
from datetime import datetime

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# Try loading LLM libraries, catching ImportError if they are missing
try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_erp.db"))

# =====================================================================
# PHASE 1: DATABASE INITIALIZATION
# =====================================================================

def init_db():
    """Initializes the SQLite database with mock ERP data."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing tables to ensure clean demo state
    cursor.execute("DROP TABLE IF EXISTS purchase_orders")
    cursor.execute("DROP TABLE IF EXISTS goods_receipts")
    cursor.execute("DROP TABLE IF EXISTS invoices")
    
    # Create Purchase Orders table (MM module)
    cursor.execute("""
        CREATE TABLE purchase_orders (
            po_id TEXT PRIMARY KEY,
            supplier_name TEXT,
            item_id TEXT,
            item_name TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_amount REAL,
            status TEXT
        )
    """)
    
    # Create Goods Receipts table (MM/Logistics module)
    cursor.execute("""
        CREATE TABLE goods_receipts (
            gr_id TEXT PRIMARY KEY,
            po_id TEXT,
            item_id TEXT,
            received_quantity INTEGER,
            received_date TEXT,
            FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id)
        )
    """)
    
    # Create Invoices table (FI module)
    cursor.execute("""
        CREATE TABLE invoices (
            invoice_id TEXT PRIMARY KEY,
            po_id TEXT,
            supplier_name TEXT,
            item_id TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_amount REAL,
            status TEXT,
            discrepancy_reason TEXT,
            post_date TEXT,
            FOREIGN KEY(po_id) REFERENCES purchase_orders(po_id)
        )
    """)
    
    # Seed Data
    pos = [
        ("PO-101", "AeroParts Inc", "PART-001", "Turbine Blade", 10, 500.0, 5000.0, "APPROVED"),
        ("PO-102", "SteelCorp", "PART-002", "Steel Beams", 50, 20.0, 1000.0, "APPROVED"),
        ("PO-103", "LogiCorp", "PART-003", "Shipping Pallets", 200, 5.0, 1000.0, "APPROVED"),
        ("PO-104", "ElectroTech", "PART-004", "Copper Wires", 100, 15.0, 1500.0, "APPROVED"),
    ]
    cursor.executemany("INSERT INTO purchase_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", pos)
    
    grs = [
        ("GR-201", "PO-101", "PART-001", 10, "2026-06-01"),
        ("GR-202", "PO-102", "PART-002", 50, "2026-06-02"),
        ("GR-203", "PO-103", "PART-003", 200, "2026-06-03"),
        # PO-104 has no goods receipt seeded (missing GR scenario)
    ]
    cursor.executemany("INSERT INTO goods_receipts VALUES (?, ?, ?, ?, ?)", grs)
    
    conn.commit()
    conn.close()
    print("Database initialized at:", DB_PATH)


# =====================================================================
# PHASE 2: LANGGRAPH CORE DEVELOPMENT
# =====================================================================

class AgentState(TypedDict):
    messages: List[BaseMessage]
    invoice_raw: Dict[str, Any]         # User submitted invoice fields
    invoice_parsed: Dict[str, Any]      # Structured extracted invoice data
    po_data: Optional[Dict[str, Any]]   # Purchase order data from DB
    gr_data: Optional[Dict[str, Any]]   # Goods receipt data from DB
    reconciliation_status: str          # MATCHED, PRICE_MISMATCH, QTY_MISMATCH, MISSING_GR, MISSING_PO, SUPPLIER_MISMATCH
    discrepancy_amount: float           # Dollar value discrepancy
    supplier_email_draft: Optional[str] # Drafted email for supplier
    post_status: str                    # PENDING, POSTED, BLOCKED_AWAITING_SUPPLIER, BLOCKED_AWAITING_MANAGER
    human_decision: Optional[str]       # APPROVED or REJECTED (HITL)
    logs: List[str]                     # Chain-of-thought logs for frontend timeline


# LLM Selection Helper
def get_llm():
    """Resolves which LLM model class to use based on environment variables."""
    mode = os.environ.get("LLM_MODE", "simulator").lower()
    
    if mode == "ollama":
        if ChatOllama is None:
            raise ImportError("ChatOllama is not available. Make sure langchain-ollama is installed.")
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "llama3")
        print(f"Configuring ChatOllama with server {url} and model {model}")
        return ChatOllama(base_url=url, model=model)
        
    elif mode == "openai":
        if ChatOpenAI is None:
            raise ImportError("ChatOpenAI is not available. Make sure langchain-openai is installed.")
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        return ChatOpenAI(api_key=api_key, model=model)
        
    elif mode == "gemini":
        if ChatGoogleGenerativeAI is None:
            raise ImportError("ChatGoogleGenerativeAI is not available. Make sure langchain-google-genai is installed.")
        api_key = os.environ.get("GEMINI_API_KEY")
        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        return ChatGoogleGenerativeAI(api_key=api_key, model=model)
        
    else:
        # Falls back to high-fidelity Simulator Mode
        return None


# ---------------------------------------------------------------------
# NODE 1: Intake Agent
# ---------------------------------------------------------------------
def intake_agent(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("Intake Agent: Activated. Parsing incoming invoice document...")
    
    raw = state["invoice_raw"]
    
    # Simulating or invoking LLM to parse/validate raw document text/dictionary
    llm = get_llm()
    if llm:
        logs.append("Intake Agent: Querying LLM to extract structured invoice metadata...")
        prompt = f"Extract structured PO ID, Supplier Name, Item ID, Quantity, Unit Price, and Invoice ID from this invoice: {raw}. Return JSON."
        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            logs.append(f"Intake Agent: LLM extracted: {res.content}")
            # In a real system, we'd JSON parse it. For robustness, we fallback if parse fails.
        except Exception as e:
            logs.append(f"Intake Agent: LLM error: {e}. Falling back to structured extraction.")
            
    # Structured extraction
    parsed = {
        "invoice_id": raw.get("invoice_id", "INV-UNKNOWN"),
        "po_id": raw.get("po_id", "").strip(),
        "supplier_name": raw.get("supplier_name", "").strip(),
        "item_id": raw.get("item_id", "").strip(),
        "quantity": int(raw.get("quantity", 0)),
        "unit_price": float(raw.get("unit_price", 0.0)),
        "total_amount": float(raw.get("total_amount", 0.0))
    }
    
    # Set default total if not provided
    if parsed["total_amount"] == 0.0:
        parsed["total_amount"] = parsed["quantity"] * parsed["unit_price"]
        
    logs.append(f"Intake Agent: Structured invoice parsed: Invoice {parsed['invoice_id']} referencing PO {parsed['po_id']}. Quantity: {parsed['quantity']}, Price: ${parsed['unit_price']:.2f}, Total: ${parsed['total_amount']:.2f}.")
    
    return {
        "invoice_parsed": parsed,
        "logs": logs
    }


# ---------------------------------------------------------------------
# NODE 2: ERP Agent
# ---------------------------------------------------------------------
def erp_agent(state: AgentState) -> Dict[str, Any]:
    logs = state["logs"].copy()
    invoice = state["invoice_parsed"]
    po_id = invoice["po_id"]
    
    logs.append(f"ERP Agent: Querying database for Purchase Order '{po_id}' and matching Goods Receipt...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Query Purchase Order
    cursor.execute("SELECT * FROM purchase_orders WHERE po_id = ?", (po_id,))
    po_row = cursor.fetchone()
    
    po_data = None
    if po_row:
        po_data = dict(po_row)
        logs.append(f"ERP Agent: Purchase Order '{po_id}' found in database. Supplier: {po_data['supplier_name']}, Item: {po_data['item_name']}, Quantity ordered: {po_data['quantity']}, Price: ${po_data['unit_price']:.2f}.")
    else:
        logs.append(f"ERP Agent: Purchase Order '{po_id}' NOT FOUND in ERP database.")
        
    # Query Goods Receipt
    cursor.execute("SELECT * FROM goods_receipts WHERE po_id = ?", (po_id,))
    gr_row = cursor.fetchone()
    
    gr_data = None
    if gr_row:
        gr_data = dict(gr_row)
        logs.append(f"ERP Agent: Goods Receipt found. Received quantity: {gr_data['received_quantity']} on {gr_data['received_date']}.")
    else:
        logs.append(f"ERP Agent: NO Goods Receipt found for Purchase Order '{po_id}'.")
        
    conn.close()
    
    return {
        "po_data": po_data,
        "gr_data": gr_data,
        "logs": logs
    }


# ---------------------------------------------------------------------
# NODE 3: Reconciliation Agent (Three-Way Match)
# ---------------------------------------------------------------------
def reconciliation_agent(state: AgentState) -> Dict[str, Any]:
    logs = state["logs"].copy()
    invoice = state["invoice_parsed"]
    po = state["po_data"]
    gr = state["gr_data"]
    
    logs.append("Reconciliation Agent: Initiating Three-Way Match (Invoice vs. Purchase Order vs. Goods Receipt)...")
    
    # Check if PO exists
    if not po:
        logs.append("Reconciliation Agent: MATCH FAILURE - Referenced PO does not exist.")
        return {
            "reconciliation_status": "MISSING_PO",
            "discrepancy_amount": invoice["total_amount"],
            "logs": logs
        }
        
    # Check if supplier names match
    if invoice["supplier_name"].lower() != po["supplier_name"].lower():
        logs.append(f"Reconciliation Agent: MATCH FAILURE - Supplier name on invoice '{invoice['supplier_name']}' does not match PO supplier '{po['supplier_name']}'.")
        return {
            "reconciliation_status": "SUPPLIER_MISMATCH",
            "discrepancy_amount": invoice["total_amount"],
            "logs": logs
        }
        
    # Check if Goods Receipt exists
    if not gr:
        logs.append("Reconciliation Agent: MATCH FAILURE - Goods Receipt is missing. Cannot verify delivery of goods.")
        return {
            "reconciliation_status": "MISSING_GR",
            "discrepancy_amount": invoice["total_amount"],
            "logs": logs
        }
        
    # Check quantity match (Invoice vs. PO vs. GR)
    invoice_qty = invoice["quantity"]
    po_qty = po["quantity"]
    gr_qty = gr["received_quantity"]
    
    qty_mismatch = False
    if invoice_qty != po_qty or invoice_qty != gr_qty:
        qty_mismatch = True
        logs.append(f"Reconciliation Agent: Quantity discrepancy detected! Invoice Qty ({invoice_qty}) | PO Qty ({po_qty}) | GR Received Qty ({gr_qty}).")
        
    # Check price match (Invoice unit price vs. PO unit price)
    invoice_price = invoice["unit_price"]
    po_price = po["unit_price"]
    
    price_mismatch = False
    if invoice_price != po_price:
        price_mismatch = True
        logs.append(f"Reconciliation Agent: Price discrepancy detected! Invoice Unit Price (${invoice_price:.2f}) does not match PO Unit Price (${po_price:.2f}).")
        
    # Compute discrepancy value
    po_total = po_qty * po_price
    invoice_total = invoice["total_amount"]
    discrepancy_amount = abs(invoice_total - po_total)
    
    # Resolve status
    if not qty_mismatch and not price_mismatch:
        reconciliation_status = "MATCHED"
        logs.append("Reconciliation Agent: SUCCESS - Three-Way Match completed successfully. Perfect alignment of quantities, unit prices, and supplier data.")
    elif price_mismatch and not qty_mismatch:
        reconciliation_status = "PRICE_MISMATCH"
        logs.append(f"Reconciliation Agent: DISCREPANCY - Price mismatch detected. Total discrepancy amount: ${discrepancy_amount:.2f}.")
    elif qty_mismatch and not price_mismatch:
        reconciliation_status = "QTY_MISMATCH"
        logs.append(f"Reconciliation Agent: DISCREPANCY - Quantity mismatch detected. Total discrepancy amount: ${discrepancy_amount:.2f}.")
    else:
        reconciliation_status = "MULTIPLE_MISMATCHES"
        logs.append(f"Reconciliation Agent: DISCREPANCY - Multiple price and quantity discrepancies detected. Total discrepancy amount: ${discrepancy_amount:.2f}.")
        
    return {
        "reconciliation_status": reconciliation_status,
        "discrepancy_amount": discrepancy_amount,
        "logs": logs
    }


# Routing function for conditional edge
def route_after_reconciliation(state: AgentState) -> str:
    status = state["reconciliation_status"]
    discrepancy = state["discrepancy_amount"]
    
    if status == "MATCHED":
        return "posting_agent"
    elif status in ["MISSING_PO", "MISSING_GR", "SUPPLIER_MISMATCH"]:
        return "posting_agent" # Will block immediately in posting
    else:
        # We have a price or quantity discrepancy
        if discrepancy >= 100.0:
            return "manager_approval_node" # Route to Human-in-the-loop portal
        else:
            return "supplier_liaison_agent" # Route to auto-resolution email drafting


# ---------------------------------------------------------------------
# NODE 4: Supplier Liaison Agent (Auto-drafts email)
# ---------------------------------------------------------------------
def supplier_liaison_agent(state: AgentState) -> Dict[str, Any]:
    logs = state["logs"].copy()
    invoice = state["invoice_parsed"]
    po = state["po_data"]
    gr = state["gr_data"]
    status = state["reconciliation_status"]
    discrepancy = state["discrepancy_amount"]
    
    logs.append("Supplier Liaison Agent: Active. Automatically drafting discrepancy resolution email to supplier...")
    
    # Email generation prompt
    subject = f"Discrepancy Notification for Invoice {invoice['invoice_id']} (PO: {invoice['po_id']})"
    
    llm = get_llm()
    email_body = ""
    
    if llm:
        prompt = (
            f"Draft a polite, professional corporate email to supplier '{invoice['supplier_name']}' regarding a discrepancy "
            f"on Invoice '{invoice['invoice_id']}' referencing Purchase Order '{invoice['po_id']}'.\n"
            f"Context:\n"
            f"- Invoice details: Quantity: {invoice['quantity']}, Unit Price: ${invoice['unit_price']:.2f}, Total: ${invoice['total_amount']:.2f}\n"
            f"- PO details: Quantity: {po['quantity']}, Unit Price: ${po['unit_price']:.2f}\n"
            f"- Goods Receipt details: Quantity delivered: {gr['received_quantity'] if gr else 0}\n"
            f"Discrepancy type: {status}. Mismatch amount: ${discrepancy:.2f}.\n"
            f"Ask the supplier to check their records and either provide a corrected invoice or issue a credit note. "
            f"Keep it concise, clear, and professional."
        )
        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            email_body = res.content
            logs.append("Supplier Liaison Agent: Custom resolution email drafted successfully using LLM.")
        except Exception as e:
            logs.append(f"Supplier Liaison Agent: LLM error while drafting email: {e}. Falling back to template.")
            
    if not email_body:
        # Template Fallback / Simulator Mode
        email_body = (
            f"Dear Accounts Receivable Team at {invoice['supplier_name']},\n\n"
            f"We are contacting you regarding Invoice {invoice['invoice_id']} dated {datetime.now().strftime('%Y-%m-%d')} "
            f"referencing our Purchase Order {invoice['po_id']}.\n\n"
            f"During our automated three-way matching audit, we identified a {status.replace('_', ' ').lower()}:\n"
            f"- Invoice: {invoice['quantity']} units @ ${invoice['unit_price']:.2f} each (Total: ${invoice['total_amount']:.2f})\n"
            f"- Purchase Order: {po['quantity']} units @ ${po['unit_price']:.2f} each (Total: ${po['quantity']*po['unit_price']:.2f})\n"
            f"- Goods Receipt: {gr['received_quantity'] if gr else 0} units registered in our warehouse.\n\n"
            f"The total variance is ${discrepancy:.2f}. "
            f"Could you please review this transaction? If an error occurred, kindly issue a corrected invoice or a credit note.\n\n"
            f"Best regards,\n"
            f"Accounts Payable Automated Audits\n"
            f"HTW Berlin Enterprise Solutions"
        )
        logs.append("Supplier Liaison Agent: Discrepancy email drafted using standardized template engine.")
        
    full_email = f"Subject: {subject}\n\n{email_body}"
    
    return {
        "supplier_email_draft": full_email,
        "post_status": "BLOCKED_AWAITING_SUPPLIER",
        "logs": logs
    }


# ---------------------------------------------------------------------
# NODE 5: Manager Approval Node (Human-in-the-Loop Interrupt)
# ---------------------------------------------------------------------
def manager_approval_node(state: AgentState) -> Dict[str, Any]:
    logs = state["logs"].copy()
    
    # Check if a decision has already been injected by the user (resume step)
    decision = state.get("human_decision")
    
    if decision:
        logs.append(f"Manager Portal: Decision received: '{decision}'.")
        return {
            "logs": logs
        }
    else:
        # Graph will halt here before entering the node due to the interrupt
        logs.append("Manager Portal: WARNING - Mismatch exceeds critical threshold ($100.00). Execution halted. Awaiting Manager Approval...")
        return {
            "post_status": "BLOCKED_AWAITING_MANAGER",
            "logs": logs
        }


def route_after_manager(state: AgentState) -> str:
    decision = state.get("human_decision")
    logs = state.get("logs", [])
    
    if decision == "APPROVED":
        return "posting_agent"
    else:
        # Default or REJECTED
        return "supplier_liaison_agent"


# ---------------------------------------------------------------------
# NODE 6: Posting Agent
# ---------------------------------------------------------------------
def posting_agent(state: AgentState) -> Dict[str, Any]:
    logs = state["logs"].copy()
    invoice = state["invoice_parsed"]
    status = state["reconciliation_status"]
    decision = state.get("human_decision")
    
    logs.append("Posting Agent: Active. Preparing transaction update...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    final_status = "BLOCKED"
    reason = f"Three-Way Match Failed ({status})"
    
    if status == "MATCHED":
        final_status = "POSTED"
        reason = "Perfect 3-Way Match"
        logs.append(f"Posting Agent: Invoice {invoice['invoice_id']} matches perfectly. Posting invoice to ERP Accounts Payable ledger (FI module)...")
    elif decision == "APPROVED":
        final_status = "POSTED"
        reason = "Manual override by manager"
        logs.append(f"Posting Agent: Invoice {invoice['invoice_id']} contains discrepancies but was APPROVED via manual manager override. Posting to ledger...")
    elif status == "MISSING_PO":
        reason = "Reference PO does not exist"
        logs.append(f"Posting Agent: CRITICAL - Invoice {invoice['invoice_id']} references an invalid PO. Blocking posting and flagging for audit.")
    elif status == "MISSING_GR":
        reason = "Goods Receipt missing"
        logs.append(f"Posting Agent: CRITICAL - No delivery receipt exists for Invoice {invoice['invoice_id']}. Blocking transaction.")
    elif status == "SUPPLIER_MISMATCH":
        reason = "Supplier mismatch"
        logs.append(f"Posting Agent: CRITICAL - Supplier mismatch on Invoice {invoice['invoice_id']}. Blocking transaction.")
    else:
        reason = f"Discrepancy blocked: {status}"
        logs.append(f"Posting Agent: Invoice {invoice['invoice_id']} has discrepancies and is rejected/blocked. Status set to BLOCKED.")
        
    # Write to local SQLite database
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO invoices (invoice_id, po_id, supplier_name, item_id, quantity, unit_price, total_amount, status, discrepancy_reason, post_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice["invoice_id"],
            invoice["po_id"],
            invoice["supplier_name"],
            invoice["item_id"],
            invoice["quantity"],
            invoice["unit_price"],
            invoice["total_amount"],
            final_status,
            reason,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        logs.append(f"Posting Agent: Database updated. Invoice {invoice['invoice_id']} status set to '{final_status}' in ERP tables.")
    except Exception as e:
        logs.append(f"Posting Agent: Error writing to ERP database: {e}")
    finally:
        conn.close()
        
    return {
        "post_status": final_status,
        "logs": logs
    }


# =====================================================================
# GRAPH COMPILATION
# =====================================================================

def build_workflow():
    workflow = StateGraph(AgentState)
    
    # Register Nodes
    workflow.add_node("intake_agent", intake_agent)
    workflow.add_node("erp_agent", erp_agent)
    workflow.add_node("reconciliation_agent", reconciliation_agent)
    workflow.add_node("supplier_liaison_agent", supplier_liaison_agent)
    workflow.add_node("manager_approval_node", manager_approval_node)
    workflow.add_node("posting_agent", posting_agent)
    
    # Define Edges
    workflow.set_entry_point("intake_agent")
    workflow.add_edge("intake_agent", "erp_agent")
    workflow.add_edge("erp_agent", "reconciliation_agent")
    
    # Conditional Edges after Reconciliation
    workflow.add_conditional_edges(
        "reconciliation_agent",
        route_after_reconciliation,
        {
            "posting_agent": "posting_agent",
            "supplier_liaison_agent": "supplier_liaison_agent",
            "manager_approval_node": "manager_approval_node"
        }
    )
    
    # Conditional Edges after Manager HITL Approval
    workflow.add_conditional_edges(
        "manager_approval_node",
        route_after_manager,
        {
            "posting_agent": "posting_agent",
            "supplier_liaison_agent": "supplier_liaison_agent"
        }
    )
    
    # Leaf Nodes route to END
    workflow.add_edge("posting_agent", END)
    workflow.add_edge("supplier_liaison_agent", END)
    
    # Compile with persistence for Human-in-the-loop support
    memory = MemorySaver()
    compiled_app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["manager_approval_node"]
    )
    
    return compiled_app

if __name__ == "__main__":
    init_db()
