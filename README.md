# Three-Way Match Invoice Reconciliation System

This repository contains an agentic AI system built with LangGraph to automate the Three-Way Match invoice auditing workflow in enterprise Accounts Payable (AP) departments. The system integrates with simulated ERP database tables representing Purchase Orders (PO) and Goods Receipts (GR) to reconcile incoming supplier invoices, flag discrepancies, draft dispute communication, and post matching transactions to the ledger.

## Features

*   **Document Intake**: Extracts structured fields from incoming supplier invoices.
*   **ERP Integration**: Queries local database records for Purchase Orders and Goods Receipts corresponding to the referenced PO ID.
*   **Three-Way Reconciliation**: Runs matching logic between Invoice quantity/price, PO quantity/price, and GR received quantity.
*   **Automated Exception Handling**: Automatically drafts dispute notifications for minor discrepancies (under $100) using a language model.
*   **Human-in-the-Loop Gate**: Pauses execution and awaits manager approval for major discrepancies (over $100).
*   **Ledger Posting**: Updates the final status of invoices in the ERP database (Posted vs. Blocked).

## Installation and Setup

### 1. Prerequisites
Ensure you have **Docker** and **Docker Compose** installed on your system.

### 2. Launch the Application
Run the following command in the root directory of the project to build the image and start the containerized application:
```bash
docker compose up --build
```
The application server will compile, perform initial database seeding if needed, and start up on port `8001`.

### 3. Access the Dashboard
Open your web browser and navigate to:
```
http://localhost:8001
```

### 4. Local Ollama Integration
The container is configured to automatically route connection pings to `http://host.docker.internal:11434` to communicate with your host machine's local Ollama server. Ensure Ollama is running on the host machine.

## Scenario Verification Guide

The web dashboard is configured with four test cases to verify different paths of the LangGraph state machine:

### Scenario A: Perfect Match
*   **Data**: Invoice matches PO and Goods Receipt records (PO-101).
*   **Behavior**: The graph automatically processes the invoice and updates the ledger status to Posted.

### Scenario B: Price Mismatch Under $100
*   **Data**: Invoice lists unit price of $5.20 vs. PO unit price of $5.00 (PO-103).
*   **Behavior**: The Reconciliation node flags the variance. Since the difference is under $100, the Liaison node drafts an automated vendor dispute email and flags the status as Blocked.

### Scenario C: Quantity Mismatch Over $100
*   **Data**: Invoice lists quantity of 100 units vs. PO quantity of 50 units (PO-102).
*   **Behavior**: The Reconciliation node flags the $1,000 variance. Execution halts at the manager approval node. The user can override and approve the invoice via the modal portal, which resumes the thread and updates the ledger to Posted.

### Scenario D: Missing Goods Receipt
*   **Data**: Invoice references PO-104 which has no delivery record (Goods Receipt) on file.
*   **Behavior**: The system blocks the invoice posting and flags it as Blocked in the database.

## Model Configuration

The Settings slideout (gear icon in the top right) allows selecting the LLM execution mode:

1.  **High-Fidelity Simulator**: Executes mock LLM reasoning traces, tool logs, and dispute emails locally without external dependencies.
2.  **Local Ollama**: Connects to a local Ollama server (default port 11434) using pulled models (such as `llama3.1` or `qwen2.5:14b`).
3.  **Cloud APIs**: Connects to OpenAI or Google Gemini. API keys can be entered directly in the slideout panel.
