# LangGraph Three-Way Match Invoice Reconciliation Agentic System

This prototype is an agentic AI system built with **LangGraph** to automate the **Three-Way Match** invoice auditing workflow in enterprise Accounts Payable (AP). It simulated a typical ERP environment (Materials Management and Financial Accounting modules like SAP S/4HANA) to audit invoices against corresponding Purchase Orders (PO) and Goods Receipts (GR), resolve minor discrepancies autonomously, and route high-value exceptions to human managers.

Developed in accordance with the course requirements for **Business Applications** (Betriebswirtschaftliche Anwendungen) at **HTW Berlin** (Prof. Dr. Robin Gubela, SoSe 2026).

---

## 🚀 Business Value & Objective

The **Three-Way Match** (Invoice vs. Purchase Order vs. Goods Receipt) is standard in corporate compliance to verify that a company only pays for what it ordered and actually received. 

*   **The Problem**: Traditional Robotic Process Automation (RPA) is rigid; slight price fluctuations, spelling variances, or rounding errors cause transactions to block, forcing humans to manually verify receipts, consult databases, and email suppliers.
*   **Our Solution**: A stateful LangGraph multi-agent system that:
    1.  **Intakes** invoices and extracts structured fields.
    2.  **Queries** simulated ERP database tables.
    3.  **Audits** records using a three-way matching audit.
    4.  **Auto-Resolves Low-Value Exceptions (<$100)**: Auto-drafts natural-language dispute emails to suppliers.
    5.  **Enforces Human-in-the-Loop (HITL) for High-Value Exceptions (>= $100)**: Interrupts execution, saves state, and awaits manager override.
    6.  **Updates Ledgers**: Posts correct/approved invoices to the ERP system or blocks invalid transactions.

---

## 🛠️ System Architecture & Workflow

The system is designed as a stateful graph using LangGraph:

```
[Start: Invoice Received]
       │
       ▼
 [Intake Agent]  ──► Extracts structured invoice metadata
       │
       ▼
  [ERP Agent]    ──► Queries SQLite for corresponding PO and Goods Receipt
       │
       ▼
 [Reconcile Agent] ──► Runs 3-way match logic and computes variance
       │
       ├─► Perfect Match ────────► [Posting Agent] ──► [Post to ERP Ledger] ──► [End]
       │
       ├─► Discrepancy < $100 ────► [Liaison Agent] ──► [Draft Supplier Email] ──► [End]
       │
       └─► Discrepancy >= $100 ───► [Manager Approval (HITL Interrupt)]
                                             │
                                             ▼ (Awaiting Manager Decision)
                                    [APPROVED / REJECTED]
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼ APPROVED                                  ▼ REJECTED
                [Posting Agent]                             [Liaison Agent]
                       │                                           │
                       ▼                                           ▼
             [Post to ERP Ledger]                      [Draft Supplier Email]
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             ▼
                                           [End]
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have **Python 3.10** or higher installed.

### 2. Install Dependencies
Run the following command to install the required packages:
```bash
pip install fastapi uvicorn langgraph langchain-community langchain-openai langchain-google-genai langchain-ollama pydantic pypdf
```

### 3. Initialize the ERP Database
Create and seed the mock ERP SQLite database by running the agent system script once:
```bash
python agent_system.py
```
This seeds the `mock_erp.db` database with sample Purchase Orders and Goods Receipts (e.g. AeroParts Inc, SteelCorp, LogiCorp, ElectroTech).

### 4. Launch the FastAPI Backend
Start the local web server:
```bash
python app.py
```
The server will launch on `http://127.0.0.1:8001`.

### 5. Open the Dashboard
Open your web browser and navigate to:
```
http://127.0.0.1:8001
```

---

## 🖥️ Live Demo & Scenario Walkthrough

The web dashboard is pre-configured with four test scenarios representing distinct branches in the LangGraph workflow:

### Scenario A: Perfect Match (Auto-Posts)
1.  Click **Perfect Match (PO-101)**.
2.  Review the populated invoice values (AeroParts Inc, Qty 10, Price $500, referencing PO-101).
3.  Click **Audit with LangGraph**.
4.  *Result*: The Intake, ERP Query, Reconciliation, and Posting agents execute in sequence (visualized on the graph). The database viewer at the bottom shows Invoice `INV-A01` successfully posted with status **POSTED**.

### Scenario B: Price Mismatch < $100 (Auto-Drafts Email)
1.  Click **Price Mismatch < $100 (PO-103)**.
2.  Notice the invoice price is $5.20, whereas the PO-103 price is $5.00 (Variance of $40.00).
3.  Click **Audit with LangGraph**.
4.  *Result*: The Reconciliation Agent flags the price mismatch. Because the variance is under the $100 threshold, the system routes to the **Supplier Liaison Agent**, which drafts a professional email requesting a credit note. The invoice is marked **BLOCKED_AWAITING_SUPPLIER**.

### Scenario C: Quantity Mismatch >= $100 (Human-in-the-Loop)
1.  Click **Qty Mismatch >= $100 (PO-102)**.
2.  The invoice quantity is 100 units, whereas PO-102 and GR-202 received quantity is 50 units (Variance of $1,000.00).
3.  Click **Audit with LangGraph**.
4.  *Result*: The Reconciliation Agent flags the variance. Since it exceeds $100, the graph **freezes execution** at the `manager_approval_node`.
5.  A **Human-in-the-Loop** modal dialog overlays the screen.
6.  Click **Override & Approve Posting**. The graph resumes from memory, routes to the posting node, and registers the invoice in the ERP database as **POSTED** with the note *"Manual override by manager"*.

### Scenario D: Missing Goods Receipt (Blocked Posting)
1.  Click **Missing Goods Receipt (PO-104)**.
2.  References PO-104 (ElectroTech), but no delivery has occurred (no GR record exists).
3.  Click **Audit with LangGraph**.
4.  *Result*: The Reconciliation Agent notes the missing Goods Receipt, blocks posting immediately, and flags the invoice as **BLOCKED** in the simulated ERP database.

---

## 🤖 Language Model Modes

The dashboard provides a **Settings panel** (gear icon in the top right) to configure how LangGraph processes audits:

1.  **High-Fidelity Simulator (Default)**: Runs locally without API keys or servers. It simulates LLM reasoning, tools, and email drafts, making it 100% reliable for class presentations.
2.  **Local Ollama**: Connects to a local Ollama instance (default `http://localhost:11434`) using models like `llama3` or `mistral` to dynamically analyze discrepancies and draft emails.
3.  **OpenAI / Google Gemini**: Connects to OpenAI (`gpt-4o-mini`) or Gemini (`gemini-1.5-flash`) APIs. Simply input your API key in the slideout panel.

---

## 📁 Directory Structure

*   `agent_system.py` - Core LangGraph workflow nodes, edges, states, and SQLite DB configuration.
*   `app.py` - FastAPI backend server mapping API requests to the compiled graph.
*   `index.html` - Dashboard HTML layout.
*   `styles.css` - Premium glassmorphism dark-theme styling sheet.
*   `app.js` - Client-side state visualizer and event bindings.
*   `test_agent.py` - Automated test suite verifying graph paths.
*   `presentation.md` - Slide deck outlines and professional speaker notes.
*   `mock_erp.db` - Local SQLite database containing PO, GR, and Invoice tables.
