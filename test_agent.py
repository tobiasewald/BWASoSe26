import os
import uuid
from agent_system import build_workflow, init_db

def run_test_scenarios():
    print("Initializing test database...")
    init_db()
    
    app = build_workflow()
    
    # Define Scenario Invoices
    scenarios = {
        "Scenario A (Perfect Match)": {
            "invoice_id": "INV-A01",
            "po_id": "PO-101",
            "supplier_name": "AeroParts Inc",
            "item_id": "PART-001",
            "quantity": 10,
            "unit_price": 500.0,
            "total_amount": 5000.0
        },
        "Scenario B (Price Mismatch < $100)": {
            "invoice_id": "INV-B02",
            "po_id": "PO-103",
            "supplier_name": "LogiCorp",
            "item_id": "PART-003",
            "quantity": 200,
            "unit_price": 5.20,
            "total_amount": 1040.0
        },
        "Scenario C (Quantity Mismatch >= $100 - Triggers HITL)": {
            "invoice_id": "INV-C03",
            "po_id": "PO-102",
            "supplier_name": "SteelCorp",
            "item_id": "PART-002",
            "quantity": 100,
            "unit_price": 20.00,
            "total_amount": 2000.0
        },
        "Scenario D (Missing Goods Receipt)": {
            "invoice_id": "INV-D04",
            "po_id": "PO-104",
            "supplier_name": "ElectroTech",
            "item_id": "PART-004",
            "quantity": 100,
            "unit_price": 15.0,
            "total_amount": 1500.0
        }
    }
    
    for name, raw_invoice in scenarios.items():
        print("\n" + "=" * 50)
        print(f"RUNNING TEST: {name}")
        print("=" * 50)
        
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        # Initial State
        initial_state = {
            "messages": [],
            "invoice_raw": raw_invoice,
            "invoice_parsed": {},
            "po_data": None,
            "gr_data": None,
            "reconciliation_status": "PENDING",
            "discrepancy_amount": 0.0,
            "supplier_email_draft": None,
            "post_status": "PENDING",
            "human_decision": None,
            "logs": []
        }
        
        # Run graph
        state = app.invoke(initial_state, config=config)
        
        # Print Logs
        print("\nAgent Logs:")
        for log in state.get("logs", []):
            print(f"  - {log}")
            
        # Check if graph is interrupted
        next_steps = app.get_state(config).next
        if next_steps:
            print(f"\nWorkflow Interrupted! Awaiting nodes: {next_steps}")
            print(f"Post Status: {state.get('post_status')}")
            
            if "manager_approval_node" in next_steps:
                print("Simulating Manager Approval...")
                # Update state with manager override
                app.update_state(config, {"human_decision": "APPROVED"}, as_node="manager_approval_node")
                print("Resuming workflow...")
                # Resume execution
                state = app.invoke(None, config=config)
                print("\nResumed Agent Logs:")
                for log in state.get("logs", []):
                    print(f"  - {log}")
                print(f"Final Invoice Status in ERP: {state.get('post_status')}")
        else:
            print(f"\nWorkflow Completed Automatically!")
            print(f"Final Invoice Status in ERP: {state.get('post_status')}")
            if state.get("supplier_email_draft"):
                print("\nDrafted Supplier Email:")
                print(state["supplier_email_draft"])

if __name__ == "__main__":
    run_test_scenarios()
