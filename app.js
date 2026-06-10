// Scenarios Data Definition
const SCENARIOS = {
    A: {
        invoice_id: "INV-A01",
        po_id: "PO-101",
        supplier_name: "AeroParts Inc",
        item_id: "PART-001",
        quantity: 10,
        unit_price: 500.00
    },
    B: {
        invoice_id: "INV-B02",
        po_id: "PO-103",
        supplier_name: "LogiCorp",
        item_id: "PART-003",
        quantity: 200,
        unit_price: 5.20
    },
    C: {
        invoice_id: "INV-C03",
        po_id: "PO-102",
        supplier_name: "SteelCorp",
        item_id: "PART-002",
        quantity: 100,
        unit_price: 20.00
    },
    D: {
        invoice_id: "INV-D04",
        po_id: "PO-104",
        supplier_name: "ElectroTech",
        item_id: "PART-004",
        quantity: 100,
        unit_price: 15.00
    }
};

// Global Application State
let currentThreadId = null;
let currentDbTable = "pos"; // pos, grs, invs

document.addEventListener("DOMContentLoaded", () => {
    // UI Elements
    const scenarioBtns = document.querySelectorAll(".scenario-btn");
    const invIdInput = document.getElementById("inv-id-input");
    const poIdInput = document.getElementById("po-id-input");
    const supplierInput = document.getElementById("supplier-input");
    const itemInput = document.getElementById("item-input");
    const qtyInput = document.getElementById("qty-input");
    const priceInput = document.getElementById("price-input");
    
    const submitBtn = document.getElementById("submit-invoice-btn");
    const resetDbBtn = document.getElementById("reset-db-btn");
    
    // Tab toggles
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabLogs = document.getElementById("tab-logs");
    const tabLiaison = document.getElementById("tab-liaison");
    
    // Database view toggles
    const dbTabBtns = document.querySelectorAll(".db-tab-btn");
    
    // Config slideout
    const configBtn = document.getElementById("config-toggle-btn");
    const configModal = document.getElementById("config-modal");
    const configCloseBtn = document.getElementById("config-close-btn");
    const configSaveBtn = document.getElementById("config-save-btn");
    const configModeSelect = document.getElementById("config-mode-select");
    
    // HITL modal
    const hitlModal = document.getElementById("hitl-modal");
    const hitlApproveBtn = document.getElementById("btn-hitl-approve");
    const hitlRejectBtn = document.getElementById("btn-hitl-reject");
    
    // =================================================================
    // INITIALIZATION & SCENARIO SELECTION
    // =================================================================
    
    // Initialize DB tables on load
    refreshDbView();
    fetchConfig();

    // Scenario Selection Handler
    scenarioBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            // Toggle active class
            scenarioBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            // Load scenario data into editor
            const sKey = btn.dataset.scenario;
            const data = SCENARIOS[sKey];
            if (data) {
                invIdInput.value = data.invoice_id;
                poIdInput.value = data.po_id;
                supplierInput.value = data.supplier_name;
                itemInput.value = data.item_id;
                qtyInput.value = data.quantity;
                priceInput.value = data.unit_price.toFixed(2);
            }
            
            // Clear graph visuals and timelines
            clearGraphVisuals();
            resetStateDisplay();
        });
    });

    // =================================================================
    // TAB TOGGLE HANDLER
    // =================================================================
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            const target = btn.dataset.tab;
            if (target === "logs") {
                tabLogs.classList.add("active");
                tabLiaison.classList.remove("active");
            } else {
                tabLogs.classList.remove("active");
                tabLiaison.classList.add("active");
            }
        });
    });

    // =================================================================
    // ERP DATABASE VIEW TAB HANDLER
    // =================================================================
    dbTabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            dbTabBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentDbTable = btn.dataset.dbTable;
            refreshDbView();
        });
    });

    // =================================================================
    // LLM CONFIGURATION MODAL SLIDEOUT
    // =================================================================
    configBtn.addEventListener("click", () => {
        configModal.classList.add("open");
    });
    
    configCloseBtn.addEventListener("click", () => {
        configModal.classList.remove("open");
    });
    
    configModeSelect.addEventListener("change", () => {
        toggleConfigFields(configModeSelect.value);
    });

    configSaveBtn.addEventListener("click", async () => {
        const payload = {
            mode: configModeSelect.value,
            ollama_url: document.getElementById("config-ollama-url").value,
            ollama_model: document.getElementById("config-ollama-model").value,
            openai_key: document.getElementById("config-openai-key").value,
            gemini_key: document.getElementById("config-gemini-key").value
        };
        
        try {
            const res = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                alert("Execution settings successfully updated.");
                configModal.classList.remove("open");
                checkModelHealth(); // Check connection immediately on save
            } else {
                alert("Failed to save configurations.");
            }
        } catch (e) {
            console.error("Config save error:", e);
            alert("Error communicating with backend server.");
        }
    });

    // =================================================================
    // INVOICE AUDIT SUBMISSION
    // =================================================================
    submitBtn.addEventListener("click", async () => {
        // Prepare payload from form
        const invoiceData = {
            invoice_id: invIdInput.value.trim(),
            po_id: poIdInput.value.trim(),
            supplier_name: supplierInput.value.trim(),
            item_id: itemInput.value.trim(),
            quantity: parseInt(qtyInput.value) || 0,
            unit_price: parseFloat(priceInput.value) || 0.0,
            total_amount: (parseInt(qtyInput.value) || 0) * (parseFloat(priceInput.value) || 0.0)
        };
        
        // 1. Reset visual interfaces
        clearGraphVisuals();
        resetStateDisplay();
        setTimelineLoading();
        submitBtn.disabled = true;
        
        try {
            // 2. Send POST to FastAPI
            const res = await fetch("/api/invoice", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(invoiceData)
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Server error.");
            }
            
            const data = await res.json();
            currentThreadId = data.thread_id;
            
            // 3. Animate the workflow graph execution sequence
            animateAuditWorkflow(data);
            
        } catch (e) {
            console.error("Audit error:", e);
            renderTimelineLogs(["Error: " + e.message], "danger");
            submitBtn.disabled = false;
        }
    });

    // =================================================================
    // HUMAN-IN-THE-LOOP PORTAL ACTION HANDLERS
    // =================================================================
    hitlApproveBtn.addEventListener("click", () => submitManagerDecision("APPROVED"));
    hitlRejectBtn.addEventListener("click", () => submitManagerDecision("REJECTED"));

    async function submitManagerDecision(decision) {
        if (!currentThreadId) return;
        
        // Close modal
        hitlModal.classList.remove("open");
        setTimelineLoading();
        
        try {
            const res = await fetch("/api/approve", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    thread_id: currentThreadId,
                    decision: decision
                })
            });
            
            if (!res.ok) {
                throw new Error("Failed to process manager decision on server.");
            }
            
            const data = await res.json();
            
            // Re-animate with updated state
            animateAuditWorkflow(data);
            
        } catch (e) {
            console.error("HITL decision error:", e);
            renderTimelineLogs(["Error: " + e.message], "danger");
        }
    }

    // =================================================================
    // DB RESET HANDLER
    // =================================================================
    resetDbBtn.addEventListener("click", async () => {
        if (!confirm("Are you sure you want to restore the mock ERP database to initial seed states?")) return;
        try {
            const res = await fetch("/api/reset-db", { method: "POST" });
            if (res.ok) {
                alert("Simulated ERP database successfully reset.");
                refreshDbView();
                clearGraphVisuals();
                resetStateDisplay();
            }
        } catch (e) {
            console.error("Reset DB error:", e);
        }
    });

    // =================================================================
    // GRAPH AND TIMELINE VISUALIZATION FUNCTIONS
    // =================================================================
    
    function animateAuditWorkflow(stateData) {
        const logs = stateData.logs;
        const totalDuration = 3500; // 3.5 seconds visualization animation
        const steps = [
            { node: "node-intake", edge: "edge-1", triggerAt: 0.1 },
            { node: "node-erp", edge: "edge-2", triggerAt: 0.35 },
            { node: "node-reconcile", triggerAt: 0.6 }
        ];
        
        // Animate initial linear sequence nodes
        steps.forEach(step => {
            setTimeout(() => {
                const nodeEl = document.getElementById(step.node);
                if (nodeEl) nodeEl.classList.add("active");
                
                if (step.edge) {
                    const edgeEl = document.getElementById(step.edge);
                    if (edgeEl) edgeEl.classList.add("active");
                }
            }, totalDuration * step.triggerAt);
        });

        // Resolve branch nodes after reconciliation completes
        setTimeout(() => {
            // Apply outcome visual stylings
            applyBranchOutcomeVisuals(stateData);
            
            // Display values in central panel display card
            updateStateDisplayCard(stateData);
            
            // Populate timeline logs and email viewer
            renderTimelineLogs(logs);
            populateEmailViewer(stateData);
            
            // Update SQLite table view at bottom
            refreshDbView();
            
            submitBtn.disabled = false;
            
            // Open HITL Approval Modal if graph was interrupted
            if (stateData.is_interrupted) {
                openManagerHITLModal(stateData);
            }
            
        }, totalDuration * 0.85);
    }
    
    function applyBranchOutcomeVisuals(stateData) {
        const status = stateData.reconciliation_status;
        const isInterrupted = stateData.is_interrupted;
        
        // Remove active state from linear nodes, replace with success styling
        document.getElementById("node-intake").className = "node active-success";
        document.getElementById("node-erp").className = "node active-success";
        document.getElementById("node-reconcile").className = "node active-success";
        
        document.getElementById("edge-1").className = "edge-connector active-success";
        document.getElementById("edge-2").className = "edge-connector active-success";
        
        // Clear branch links
        document.getElementById("edge-diag-up").className = "edge-connector edge-diagonal-up";
        document.getElementById("edge-straight").className = "edge-connector edge-straight";
        document.getElementById("edge-diag-down").className = "edge-connector edge-diagonal-down";
        
        document.getElementById("node-posting").className = "node";
        document.getElementById("node-liaison").className = "node";
        document.getElementById("node-manager").className = "node";

        if (status === "MATCHED" || stateData.human_decision === "APPROVED") {
            // Scenario A / Approved Scenario C: Posting Path
            document.getElementById("edge-diag-up").classList.add("active-success");
            document.getElementById("node-posting").classList.add("active-success");
        } else if (isInterrupted) {
            // Scenario C: Interrupted Manager Path
            document.getElementById("edge-diag-down").classList.add("active-warning");
            document.getElementById("node-manager").classList.add("active-warning");
        } else if (status === "PRICE_MISMATCH" || status === "QTY_MISMATCH" || status === "MULTIPLE_MISMATCHES" || stateData.post_status === "BLOCKED_AWAITING_SUPPLIER" || stateData.human_decision === "REJECTED") {
            // Scenario B: Email liaison path
            document.getElementById("edge-straight").classList.add("active-warning");
            document.getElementById("node-liaison").classList.add("active-warning");
        } else {
            // Scenario D / Blocks: Posting blocked
            document.getElementById("edge-diag-up").classList.add("active-danger");
            document.getElementById("node-posting").classList.add("active-danger");
        }
    }
    
    function updateStateDisplayCard(stateData) {
        const recStatusEl = document.getElementById("state-reconciliation-status");
        const discEl = document.getElementById("state-discrepancy");
        const postStatusEl = document.getElementById("state-post-status");
        
        const status = stateData.reconciliation_status;
        const postStatus = stateData.post_status;
        
        // Reconciliation status badge
        recStatusEl.textContent = status.replace("_", " ");
        recStatusEl.className = "state-val";
        
        if (status === "MATCHED") {
            recStatusEl.classList.add("val-matched");
        } else if (status === "PENDING") {
            recStatusEl.classList.add("val-pending");
        } else if (status === "MISSING_PO" || status === "MISSING_GR" || status === "SUPPLIER_MISMATCH") {
            recStatusEl.classList.add("val-blocked");
        } else {
            recStatusEl.classList.add("val-mismatch");
        }
        
        // Discrepancy Amount
        discEl.textContent = `$${stateData.discrepancy_amount.toFixed(2)}`;
        if (stateData.discrepancy_amount > 0) {
            discEl.style.color = "var(--warning)";
        } else {
            discEl.style.color = "var(--success)";
        }
        
        // Posting status badge
        postStatusEl.textContent = postStatus.replace(/_AWAITING_/, " (Wait: ").replace(/_/, " ") + (postStatus.includes("AWAITING") ? ")" : "");
        postStatusEl.className = "state-val";
        
        if (postStatus === "POSTED") {
            postStatusEl.classList.add("val-matched");
        } else if (postStatus === "PENDING") {
            postStatusEl.classList.add("val-pending");
        } else {
            postStatusEl.classList.add("val-blocked");
        }
    }

    function openManagerHITLModal(stateData) {
        const inv = stateData.invoice_parsed;
        const po = stateData.po_data;
        
        document.getElementById("modal-inv-id").textContent = inv.invoice_id;
        document.getElementById("modal-supplier").textContent = inv.supplier_name;
        
        const invTotal = inv.total_amount;
        const poTotal = po ? (po.quantity * po.unit_price) : 0;
        
        document.getElementById("modal-invoice-val").textContent = `$${invTotal.toFixed(2)}`;
        document.getElementById("modal-po-val").textContent = `$${poTotal.toFixed(2)}`;
        document.getElementById("modal-variance-val").textContent = `$${stateData.discrepancy_amount.toFixed(2)}`;
        
        let qtyText = `Invoice: ${inv.quantity} units vs. PO: ${po ? po.quantity : 0} units`;
        if (stateData.gr_data) {
            qtyText += ` (Delivered: ${stateData.gr_data.received_quantity} units)`;
        }
        document.getElementById("modal-qty").textContent = qtyText;
        
        hitlModal.classList.add("open");
    }

    function populateEmailViewer(stateData) {
        const emailBodyEl = document.getElementById("email-body-content");
        const sendEmailBtn = document.getElementById("send-email-btn");
        
        if (stateData.supplier_email_draft) {
            // Split subject and body
            const emailText = stateData.supplier_email_draft;
            const lines = emailText.split("\n");
            
            let subject = "Discrepancy Audit Notification";
            let body = emailText;
            
            if (lines[0].startsWith("Subject:")) {
                subject = lines[0].replace("Subject:", "").trim();
                body = lines.slice(1).join("\n").trim();
            }
            
            document.getElementById("email-to").textContent = `${stateData.invoice_parsed.supplier_name.toLowerCase().replace(/\s+/g, '')}@vendor.com`;
            document.getElementById("email-subject").textContent = subject;
            emailBodyEl.textContent = body;
            
            sendEmailBtn.classList.remove("hidden");
            sendEmailBtn.onclick = () => {
                alert("Supplier notification dispute email sent successfully.");
                sendEmailBtn.classList.add("hidden");
            };
            
            // Switch tabs automatically to email tab to show work
            document.querySelector(".tab-btn[data-tab='liaison']").click();
        } else {
            document.getElementById("email-to").textContent = "supplier@company.com";
            document.getElementById("email-subject").textContent = "-";
            emailBodyEl.textContent = "Select Scenario B to automatically generate a supplier notification email draft.";
            sendEmailBtn.classList.add("hidden");
            
            // Ensure logs tab is selected
            document.querySelector(".tab-btn[data-tab='logs']").click();
        }
    }

    function renderTimelineLogs(logs, customStatus = null) {
        const timeline = document.getElementById("log-timeline");
        timeline.innerHTML = "";
        
        if (!logs || logs.length === 0) {
            timeline.innerHTML = `
                <div class="timeline-empty">
                    <p>No audit logs populated.</p>
                </div>`;
            return;
        }
        
        logs.forEach((log, index) => {
            const item = document.createElement("div");
            item.className = "log-item";
            
            const bullet = document.createElement("div");
            bullet.className = "log-bullet";
            
            // Highlight bullets based on status text keywords
            if (customStatus) {
                bullet.classList.add(`${customStatus}-bullet`);
            } else if (log.includes("SUCCESS") || log.includes("Perfect")) {
                bullet.classList.add("success-bullet");
            } else if (log.includes("WARNING") || log.includes("discrepancy") || log.includes("discrepancies")) {
                bullet.classList.add("warning-bullet");
            } else if (log.includes("CRITICAL") || log.includes("Error") || log.includes("FAILURE")) {
                bullet.classList.add("danger-bullet");
            } else if (index === logs.length - 1) {
                bullet.classList.add("active-bullet");
            }
            
            const text = document.createElement("div");
            text.className = "log-text";
            
            // Format timestamps or agent headers bold
            let formattedLog = log;
            const colonIdx = log.indexOf(":");
            if (colonIdx > 0 && colonIdx < 30) {
                const header = log.substring(0, colonIdx + 1);
                const desc = log.substring(colonIdx + 1);
                formattedLog = `<strong>${header}</strong>${desc}`;
            }
            
            text.innerHTML = formattedLog;
            
            item.appendChild(bullet);
            item.appendChild(text);
            timeline.appendChild(item);
        });
    }

    function setTimelineLoading() {
        const timeline = document.getElementById("log-timeline");
        timeline.innerHTML = `
            <div class="timeline-empty">
                <div class="node-pulse" style="width:40px; height:40px; border:3px solid var(--primary); border-radius:50%; margin: 0 auto 12px auto; animation: node-pulse-anim 1s infinite;"></div>
                <p>LangGraph multi-agent workflow actively running in backend...</p>
            </div>`;
    }

    function clearGraphVisuals() {
        const nodes = document.querySelectorAll(".node");
        const edges = document.querySelectorAll(".edge-connector");
        
        nodes.forEach(n => {
            n.className = "node";
        });
        edges.forEach(e => {
            e.className = e.id.includes("diag-up") ? "edge-connector edge-diagonal-up" :
                        e.id.includes("diag-down") ? "edge-connector edge-diagonal-down" :
                        e.id.includes("straight") ? "edge-connector edge-straight" :
                        "edge-connector";
        });
    }

    function resetStateDisplay() {
        document.getElementById("state-reconciliation-status").className = "state-val val-pending";
        document.getElementById("state-reconciliation-status").textContent = "Awaiting Run";
        document.getElementById("state-discrepancy").textContent = "$0.00";
        document.getElementById("state-discrepancy").style.color = "var(--text-main)";
        document.getElementById("state-post-status").className = "state-val val-pending";
        document.getElementById("state-post-status").textContent = "Pending";
    }

    // =================================================================
    // CONFIGURATION AND SETTINGS FORM MANAGEMENT
    // =================================================================
    
    function toggleConfigFields(mode) {
        document.querySelectorAll(".config-conditional").forEach(el => el.classList.remove("active"));
        if (mode === "ollama") {
            document.getElementById("config-ollama-fields").classList.add("active");
        } else if (mode === "openai") {
            document.getElementById("config-openai-fields").classList.add("active");
        } else if (mode === "gemini") {
            document.getElementById("config-gemini-fields").classList.add("active");
        }
    }

    async function fetchConfig() {
        try {
            const res = await fetch("/api/config");
            if (res.ok) {
                const config = await res.json();
                configModeSelect.value = config.mode;
                document.getElementById("config-ollama-url").value = config.ollama_url;
                document.getElementById("config-ollama-model").value = config.ollama_model;
                toggleConfigFields(config.mode);
            }
        } catch (e) {
            console.error("Fetch config error:", e);
        }
    }

    // =================================================================
    // LOCAL SQLITE ERP DATABASE VIEWER REFRESH
    // =================================================================
    
    async function refreshDbView() {
        const tableHeader = document.querySelector("#db-table thead");
        const tableBody = document.getElementById("db-table-body");
        
        try {
            const res = await fetch("/api/db");
            if (!res.ok) throw new Error("Could not fetch database records.");
            const data = await res.json();
            
            tableHeader.innerHTML = "";
            tableBody.innerHTML = "";
            
            if (currentDbTable === "pos") {
                // Render Purchase Orders Table
                tableHeader.innerHTML = `
                    <tr>
                        <th>PO ID</th>
                        <th>Supplier</th>
                        <th>Item ID</th>
                        <th>Item Description</th>
                        <th>Quantity Ordered</th>
                        <th>Unit Price ($)</th>
                        <th>Total Val ($)</th>
                        <th>PO Status</th>
                    </tr>
                `;
                
                if (data.purchase_orders.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center">No records.</td></tr>`;
                    return;
                }
                
                data.purchase_orders.forEach(po => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${po.po_id}</strong></td>
                        <td>${po.supplier_name}</td>
                        <td><code>${po.item_id}</code></td>
                        <td>${po.item_name}</td>
                        <td>${po.quantity}</td>
                        <td>${po.unit_price.toFixed(2)}</td>
                        <td><strong>${po.total_amount.toFixed(2)}</strong></td>
                        <td><span style="color:var(--success)">${po.status}</span></td>
                    `;
                    tableBody.appendChild(tr);
                });
                
            } else if (currentDbTable === "grs") {
                // Render Goods Receipts Table
                tableHeader.innerHTML = `
                    <tr>
                        <th>GR Receipt ID</th>
                        <th>Reference PO ID</th>
                        <th>Item ID</th>
                        <th>Received Quantity</th>
                        <th>Delivery Date</th>
                    </tr>
                `;
                
                if (data.goods_receipts.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center">No records.</td></tr>`;
                    return;
                }
                
                data.goods_receipts.forEach(gr => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = `
                        <td><strong>${gr.gr_id}</strong></td>
                        <td><code>${gr.po_id}</code></td>
                        <td><code>${gr.item_id}</code></td>
                        <td><strong>${gr.received_quantity}</strong></td>
                        <td>${gr.received_date}</td>
                    `;
                    tableBody.appendChild(tr);
                });
                
            } else if (currentDbTable === "invs") {
                // Render Invoices Table
                tableHeader.innerHTML = `
                    <tr>
                        <th>Invoice ID</th>
                        <th>Reference PO ID</th>
                        <th>Supplier Name</th>
                        <th>Quantity Billed</th>
                        <th>Unit Price ($)</th>
                        <th>Invoice Amount ($)</th>
                        <th>Audit Status</th>
                        <th>Status Detail / Exception Reason</th>
                        <th>Processing Date</th>
                    </tr>
                `;
                
                if (data.invoices.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center">No invoices posted or audit exceptions stored yet. Run an audit scenario above.</td></tr>`;
                    return;
                }
                
                data.invoices.forEach(inv => {
                    const tr = document.createElement("tr");
                    
                    let statusColor = "var(--text-muted)";
                    if (inv.status === "POSTED") statusColor = "var(--success)";
                    else if (inv.status === "BLOCKED") statusColor = "var(--danger)";
                    else if (inv.status.includes("AWAITING")) statusColor = "var(--warning)";
                    
                    tr.innerHTML = `
                        <td><strong>${inv.invoice_id}</strong></td>
                        <td><code>${inv.po_id}</code></td>
                        <td>${inv.supplier_name}</td>
                        <td>${inv.quantity}</td>
                        <td>${inv.unit_price.toFixed(2)}</td>
                        <td><strong>${inv.total_amount.toFixed(2)}</strong></td>
                        <td><span style="color:${statusColor}; font-weight:bold">${inv.status}</span></td>
                        <td style="color:var(--text-muted)"><em>${inv.discrepancy_reason || "-"}</em></td>
                        <td>${inv.post_date}</td>
                    `;
                    tableBody.appendChild(tr);
                });
            }
            
        } catch (e) {
            console.error("Refresh DB table view error:", e);
            tableBody.innerHTML = `<tr><td colspan="10" style="color:var(--danger)">Error: ${e.message}</td></tr>`;
        }
    }

    async function checkModelHealth() {
        const statusDot = document.getElementById("status-dot");
        const statusText = document.getElementById("status-text");
        if (!statusDot || !statusText) return;
        
        try {
            const res = await fetch("/api/health");
            if (res.ok) {
                const health = await res.json();
                statusText.textContent = health.details;
                
                // Clear inline style and set classes
                statusDot.style.background = "";
                statusDot.className = "status-dot";
                if (health.status === "connected") {
                    statusDot.classList.add("status-dot-connected");
                } else if (health.status === "warning") {
                    statusDot.classList.add("status-dot-warning");
                } else {
                    statusDot.classList.add("status-dot-disconnected");
                }
            } else {
                statusText.textContent = "Server connection lost";
                statusDot.style.background = "";
                statusDot.className = "status-dot status-dot-disconnected";
            }
        } catch (e) {
            console.error("Health check error:", e);
            statusText.textContent = "Backend offline";
            statusDot.style.background = "";
            statusDot.className = "status-dot status-dot-disconnected";
        }
    }

    // Run health check initially and poll every 5s
    checkModelHealth();
    setInterval(checkModelHealth, 5000);
});
