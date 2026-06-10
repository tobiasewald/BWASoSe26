# Presentation Slides & Speaker Notes: LangGraph - Business

> [!NOTE]
> **HTW Berlin Presentation Guidelines**: This presentation is structured as a 6-slide deck to stay within the 7-slide limit and focus on content and live demo as the core. The speaker notes are written in a first-person, natural speaking style to help you deliver a cohesive presentation and excel in the Q&A.

---

## Slide 1: Title Slide
**Visual Layout**: Sleek, minimalist design. A dark background with an indigo accent. A clean title and sub-headline.

### Slide Content
*   **Title**: Reimagining Accounts Payable: An Agentic AI Approach to Three-Way Match Reconciliation
*   **Subtitle**: Stateful Multi-Agent Automation in ERP Materials Management and Financial Accounting
*   **Course**: Business Applications (Betriebswirtschaftliche Anwendungen)
*   **Professor**: Prof. Dr. Robin Gubela | HTW Berlin (SoSe 2026)
*   **Group Topic**: LangGraph - Business
*   **Presenters**: [Your Names]

### Speaker Notes
> "Good afternoon, everyone, and welcome to our presentation. Today, we are excited to showcase our prototype, which applies state-of-the-art agentic AI to solve a major administrative bottleneck in enterprise resource planning. Specifically, we've built a multi-agent system using LangGraph that automates the 'Three-Way Match' invoice reconciliation process in Accounts Payable. Our focus today is to show how moving from rigid rules to adaptive AI agents can unlock real business value while keeping humans in the loop for critical financial decisions."

---

## Slide 2: The Problem (The ERP Bottleneck)
**Visual Layout**: Two-column contrast. Left column: Traditional RPA limits. Right column: The manual cost of resolving invoice discrepancies.

### Slide Content
*   **Traditional Process**: The Three-Way Match (Invoice vs. Purchase Order vs. Goods Receipt) is the control standard for Accounts Payable (AP).
*   **Rigid RPA Limitations**: Standard RPA handles perfect matches but crashes on slight data format variations or minor price/quantity discrepancies.
*   **Business Cost**:
    *   AP staff spend up to **70% of their time** tracking down paper trails, contacting warehouses, or emailing suppliers.
    *   Transaction blockages lead to missed early-payment discounts and strained supplier relationships.
    *   High volume of micro-discrepancies (under $50) costs more to manually resolve than the discrepancy itself.

### Speaker Notes
> "Let’s start with the business problem. In any mid-to-large size company, when a supplier sends an invoice, the finance team must check it against two other documents before paying: the original Purchase Order and the Goods Receipt from the warehouse. This is known as the Three-Way Match. 
> 
> While standard Robotic Process Automation, or RPA, works fine for a perfect match, it is extremely fragile. If the supplier changes their invoice format, or if there is a tiny rounding difference of a few cents, RPA fails. It flags the transaction, blocks the payment, and throws it to a human accountant. The accountant then has to dig through databases, call the warehouse, and write emails to the supplier. This manual work accounts for up to 70% of AP overhead, leading to high processing costs and delayed supplier payments."

---

## Slide 3: Target Group & Objective
**Visual Layout**: Bulleted list with icons. Bold, clear focus on target roles and measurable objectives.

### Slide Content
*   **Target Group**:
    *   Accounts Payable (AP) Teams & Shared Service Centers
    *   Finance Managers & Compliance Officers
    *   Procurement & Materials Management (MM) Officers
*   **System Objectives**:
    *   **Automate Auditing**: Perform the Three-Way Match verification autonomously.
    *   **Automate Low-Value Work**: Draft and stage dispute emails to suppliers for minor variances (<$100) without human intervention.
    *   **Enforce Compliance (HITL)**: Implement a hard stop and route to a Manager Portal for high-value variances (>$100).
    *   **Maintain ERP Integrity**: Automatically post approved Invoices or block incorrect ones in the ERP system database.

### Speaker Notes
> "Our target audience includes accounts payable teams, corporate controllers, and procurement managers who handle thousands of transactions weekly. 
> 
> Our objectives were clear: We wanted to automate the routine auditing work, but more importantly, we wanted to build a system that *resolves* discrepancies, not just flags them. For minor variances—say, a supplier billing us an extra five dollars for shipping—it doesn't make economic sense for an accountant to spend 30 minutes writing an email. Our agent drafts that email autonomously. However, for significant variances, we need strict controls. So, our objective was to design a 'Human-in-the-Loop' gate using LangGraph's checkpointer, ensuring a manager must manually review and override any high-value discrepancies before they hit the financial ledger."

---

## Slide 4: Selected Framework & Agent Capabilities
**Visual Layout**: System architecture diagram (refer to the flowchart in our README/Plan). Boxes representing the distinct agents.

### Slide Content
*   **Why LangGraph?** Best suited for stateful, cyclic, and multi-agent workflows that require human interruption and persistence.
*   **State Schema**: Centralized memory containing invoice details, database queries, logs, and approval decisions.
*   **Multi-Agent Collaborative Roles**:
    1.  **Intake Agent**: Extracts structured metadata from unstructured invoice documents.
    2.  **ERP Agent**: Queries the database to retrieve corresponding PO and Goods Receipt records.
    3.  **Reconciliation Agent**: Implements the matching logic and calculates variances.
    4.  **Supplier Liaison Agent**: Drafts natural-language dispute emails.
    5.  **Posting Agent**: Updates the final ERP database ledgers.
*   **Human-in-the-Loop Node**: Freezes state using checkpointers, waiting for manager action.

### Speaker Notes
> "To build this, we chose LangGraph as our framework. While other tools like AutoGen are great for open-ended agent chat, LangGraph is the industry standard for structured, cyclic business workflows. It allows us to model our business logic as a state graph, where nodes are specialized agents and edges define the routing rules. 
> 
> We have five distinct agents working together. The Intake Agent extracts the invoice data, the ERP Agent queries our mock database to fetch the corresponding PO and warehouse receipts, and the Reconciliation Agent runs the matching logic. If a discrepancy is found, LangGraph routes the workflow dynamically. For minor variances, it routes to the Supplier Liaison Agent, which drafts a custom email using the LLM. For major variances, the graph triggers an interrupt, freezing its state in memory, and waits for a human manager to approve or reject the override via our web portal."

---

## Slide 5: Live Demo (Main Focus)
**Visual Layout**: Large screenshot or browser window containing our web application dashboard. Highlights the node visualizer and scenario selectors.

### Slide Content
*   **Interactive AP Audit Dashboard**:
    *   **Four Scenarios Tested**:
        *   *Scenario A (Perfect Match)*: Auto-posts to ERP.
        *   *Scenario B (Price Mismatch < $100)*: Auto-drafts vendor email.
        *   *Scenario C (Qty Mismatch >= $100)*: Pauses for manager approval.
        *   *Scenario D (Missing Goods Receipt)*: Auto-blocks invoice.
    *   **Real-time Node Graph Visualizer**: Shows active node states and routing.
    *   **Reasoning Timeline**: Displays detailed agent thinking logs.
    *   **Live ERP Database Viewer**: Live updates in simulated SQLite tables.

### Speaker Notes
> "Let’s dive into the core of our presentation: the live demo. We’ve built a premium AP Audit Dashboard that connects our LangGraph backend with a web-based interface.
> 
> *[Action: Transition to Demo]*
> As you can see, on the left we have our scenario selector. If we click 'Scenario A', the agents verify a perfect match and post it instantly. Look at the center panel—you can see the Intake, ERP Query, and Reconciliation nodes light up in green, routing directly to the Post node. The SQLite viewer at the bottom shows the invoice status updated to 'POSTED'.
> 
> Now, look at 'Scenario B', where a small price discrepancy of $40 is detected. The graph routes to the Liaison node, which automatically drafts a professional dispute email in our tab view.
> 
> Finally, 'Scenario C' has a quantity discrepancy of $1,000. When we run this, the graph pauses, and a 'Human-in-the-Loop' prompt overlays the screen. As a manager, I can review the variance, click 'Override & Approve', and watch the graph resume from memory, finalize the audit, and post it to the database. This showcases the power of stateful human-AI collaboration."

---

## Slide 6: Conclusion & Takeaways
**Visual Layout**: Clean grid summarizing takeaways. Emphasizes the shift in organizational readiness.

### Slide Content
*   **Takeaways**:
    1.  **RPA vs. AI Agents**: Agents replace rigid, brittle automation with flexible, context-aware decision-making.
    2.  **State Management is Critical**: LangGraph checkpointers are essential for asynchronous business workflows that require days of pause (e.g. waiting for a manager).
    3.  **Human-AI Synergy (Levels of Autonomy)**: The system moves from a simple Copilot (low autonomy) to an Autonomous Worker (high autonomy) under strict, rule-based governance.
    4.  **Workplace Readiness**: Implementing agents requires structured data access (APIs) and upskilling workers to manage agent exceptions.

### Speaker Notes
> "To conclude, here are our main takeaways. 
> 
> First, our prototype demonstrates the shift from linear RPA to dynamic, agentic workflows. By using LLMs, the system doesn't crash when it encounters minor errors; it actively works to resolve them by drafting communication. 
> 
> Second, state management is the key to business agents. Business processes are rarely completed in a single session. They require waiting for human reviews, warehouse updates, or supplier replies. LangGraph's checkpointer lets us freeze the agent's state, release server resources, and resume the audit days later without losing context.
> 
> Finally, we see this as a perfect example of high-autonomy collaboration. The agent handles 90% of the tedious work, while humans are elevated to high-value governors of the system, stepping in only for compliance overrides. 
> 
> Thank you for your attention, and we are now open for your questions."
