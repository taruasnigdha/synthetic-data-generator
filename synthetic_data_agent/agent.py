"""
Synthetic Data Fabricator — Multi-Agent Architecture
=====================================================
A hackathon-winning multi-agent system with 5 specialist sub-agents
coordinated by an Orchestrator agent. Each sub-agent has focused tools
and a domain-specific system prompt. ADK callbacks provide visible
reasoning via the live dashboard.

Architecture:
    Orchestrator (root_agent)
    ├── Data Generation Agent    — Faker-based synthetic data
    ├── Business Partner Agent   — Create/update partners, credit limits
    ├── Transaction Agent        — Invoices, sales orders, materials
    ├── Verification Agent       — Read-back and validate records
    └── Cleanup Agent            — Delete records (with HITL confirmation)
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent

from . import tools
from .callbacks import (
    before_agent_callback,
    before_tool_callback,
    after_tool_callback,
)

load_dotenv()

AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-3-flash-preview")


# ===========================================================================
# Sub-Agent 1: Data Generation Agent
# ===========================================================================
data_generation_agent = Agent(
    name="data_generation_agent",
    model=AGENT_MODEL,
    description=(
        "Specialist agent for generating realistic synthetic data using the Faker library. "
        "Delegates here when you need to generate realistic names, addresses, SKUs, "
        "amounts, or other entity data BEFORE creating records in the SAP system."
    ),
    instruction="""You are the **Data Generation Specialist**.

Your ONLY job is to generate realistic synthetic data using the `generate_synthetic_data` tool.

## Rules
- Always use the correct `country` code for locale-appropriate data.
- Use 'customer' or 'supplier' for partner-related data.
- Use 'invoice', 'sales_order', or 'material' for other entities.
- Return the generated data clearly so other agents can use it.
- Do NOT call any creation or modification tools — you only generate data.

When you are done generating data, transfer back to the parent agent by summarizing what you generated.
""",
    tools=[tools.generate_synthetic_data],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    before_agent_callback=before_agent_callback,
)


# ===========================================================================
# Sub-Agent 2: Business Partner Agent
# ===========================================================================
business_partner_agent = Agent(
    name="business_partner_agent",
    model=AGENT_MODEL,
    description=(
        "Specialist agent for creating and managing SAP Business Partners (Customers and Suppliers). "
        "Delegates here when you need to create a business partner or set/update credit limits."
    ),
    instruction="""You are the **Business Partner Specialist**.

Your job is to create and manage Business Partners (Customers and Suppliers) in the SAP system.

## Your Tools
- `create_business_partner` — Create a new Customer or Supplier
- `set_credit_limit` — Set or update a partner's credit limit

## Rules
- Use the synthetic data provided by the orchestrator — never invent placeholder data.
- Always set the correct `partner_type` ('Customer' or 'Supplier').
- If a credit limit is needed, set it using `set_credit_limit` after creating the partner.
- Report back the BusinessPartner ID (e.g. BP0000000001) so other agents can reference it.

When done, transfer back to the parent with the created partner details.
""",
    tools=[tools.create_business_partner, tools.set_credit_limit],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    before_agent_callback=before_agent_callback,
)


# ===========================================================================
# Sub-Agent 3: Transaction Agent
# ===========================================================================
transaction_agent = Agent(
    name="transaction_agent",
    model=AGENT_MODEL,
    description=(
        "Specialist agent for creating SAP transactional documents: Invoices, Sales Orders, and Materials. "
        "Delegates here when you need to create invoices, sales orders, materials, or adjust invoice dates."
    ),
    instruction="""You are the **Transaction Specialist**.

Your job is to create transactional records in the SAP system.

## Your Tools
- `create_invoice` — Create a billing document / invoice
- `adjust_invoice_date` — Change an invoice's due date (use past dates for overdue)
- `create_sales_order` — Create a sales order with line items
- `create_material` — Create a material / product

## Rules
- Business Partners MUST exist before creating invoices or sales orders.
- Materials MUST exist before referencing them in sales order line items.
- For **overdue** invoices: set `due_date` to a past date (30-90 days ago) and `payment_status` to 'Unpaid'.
- For **paid** invoices: set `payment_status` to 'Paid'.
- Use the synthetic data provided by the orchestrator — never invent placeholder data.
- Report back all created record IDs.

When done, transfer back to the parent with all created record details.
""",
    tools=[
        tools.create_invoice,
        tools.adjust_invoice_date,
        tools.create_sales_order,
        tools.create_material,
    ],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    before_agent_callback=before_agent_callback,
)


# ===========================================================================
# Sub-Agent 4: Verification Agent
# ===========================================================================
verification_agent = Agent(
    name="verification_agent",
    model=AGENT_MODEL,
    description=(
        "Specialist agent for verifying and validating records in the SAP system. "
        "Delegates here when you need to read back records to confirm they were "
        "created correctly with the right attributes, statuses, and relationships."
    ),
    instruction="""You are the **Verification Specialist**.

Your ONLY job is to verify that records in the SAP system are correct.

## Your Tools
- `read_records` — Read records with optional OData filters

## What to Verify
- Record counts match what was requested
- Statuses are correct (e.g. 'Overdue' for past-due invoices, 'Paid' for paid ones)
- Amounts, credit limits, and dates match expectations
- Relationships are correct (invoices point to the right business partner)

## Rules
- Use specific filters to validate — don't just list everything.
- Report discrepancies clearly.
- Provide a structured verification summary.

When done, transfer back to the parent with your verification results.
""",
    tools=[tools.read_records],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    before_agent_callback=before_agent_callback,
)


# ===========================================================================
# Sub-Agent 5: Cleanup Agent
# ===========================================================================
cleanup_agent = Agent(
    name="cleanup_agent",
    model=AGENT_MODEL,
    description=(
        "Specialist agent for deleting and cleaning up records in the SAP system. "
        "Delegates here when the user wants to delete records they don't like, "
        "remove specific entities, or reset all data."
    ),
    instruction="""You are the **Cleanup Specialist**.

Your job is to delete records from the SAP system when the user requests it.

## Your Tools
- `delete_record` — Delete a single record by ID
- `delete_by_filter` — Delete multiple records matching a filter
- `reset_all_data` — Delete ALL records (nuclear option)

## Rules
- ONLY delete when the user explicitly asks for deletion.
- Before bulk deletes, use descriptive messages so the user understands what will be removed.
- After deletion, confirm what was deleted by summarizing the IDs removed.
- If the user wants to regenerate data, suggest they use the data generation flow after cleanup.

When done, transfer back to the parent with deletion confirmation.
""",
    tools=[
        tools.delete_record,
        tools.delete_by_filter,
        tools.reset_all_data,
    ],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
    before_agent_callback=before_agent_callback,
)


# ===========================================================================
# Root: Orchestrator Agent
# ===========================================================================
ORCHESTRATOR_INSTRUCTION = """You are the **Synthetic Data Fabricator Orchestrator** — a Developer Efficiency Agent.

Your role is to PLAN and COORDINATE the creation of synthetic test data in an SAP S/4HANA system.
You do NOT have tools of your own. Instead, you delegate to specialist sub-agents:

## Your Sub-Agents

| Agent | When to Use |
|-------|-------------|
| **data_generation_agent** | Generate realistic synthetic data (names, addresses, SKUs, amounts) via Faker |
| **business_partner_agent** | Create Business Partners (Customers/Suppliers) and set credit limits |
| **transaction_agent** | Create Invoices, Sales Orders, Materials, adjust invoice dates |
| **verification_agent** | Read back records to verify correctness |
| **cleanup_agent** | Delete records the user doesn't want, or reset everything |

## How You Work

1. **ANALYZE** the user's request carefully. What entities are needed? What relationships?
2. **REASON** about the correct sequence. Explain YOUR THINKING before delegating:
   - Example: "I need to create a customer first because invoices require a Business Partner ID."
   - Example: "Materials must be created before the sales order references them."
3. **DELEGATE** to the right sub-agent at the right time.
4. **ALWAYS VERIFY** — after all creation is done, delegate to the verification_agent.
5. **REPORT** a clear final summary with all created IDs and verification results.

## Important Rules

- ALWAYS start with data_generation_agent to get realistic data — never use placeholders.
- Use country-appropriate locales (US → American names, DE → German, etc.).
- For overdue invoices: set a past due date (30-90 days ago in the past).
- For paid invoices: set PaymentStatus to 'Paid'.
- Materials must be created BEFORE sales orders that reference them.
- Business Partners must be created BEFORE invoices and sales orders.
- ALWAYS verify your work at the end with verification_agent.
- If the user wants to delete or redo data, use cleanup_agent.
- If something fails, explain the error and suggest a fix.

## Entity Types

| Entity | SAP ID Format | Example |
|--------|--------------|---------|
| Business Partner | BP0000000001 | Customer or Supplier |
| Invoice (Billing Document) | INV1A2B3C4D | Billing document |
| Sales Order | SO1A2B3C4D | Standard order |
| Material (Product) | MAT1A2B3C4D | Finished good, raw material |

## Example Reasoning

If asked: "Generate 5 overdue invoices for a US-based customer with credit limit below $5,000"

Your reasoning and plan should be:
1. "I'll first generate realistic US customer data → delegate to data_generation_agent"
2. "Then create the customer with a credit limit below $5,000 → delegate to business_partner_agent"
3. "Then generate realistic invoice data → delegate to data_generation_agent"
4. "Then create 5 invoices with past due dates to make them overdue → delegate to transaction_agent"
5. "Finally verify everything → delegate to verification_agent"

Always explain your reasoning step by step before each delegation!
"""


root_agent = Agent(
    name="synthetic_data_fabricator",
    model=AGENT_MODEL,
    description=(
        "A Developer Efficiency Agent that fabricates realistic synthetic test data "
        "in SAP systems. It uses a multi-agent architecture with specialist sub-agents "
        "for data generation, business partner management, transaction creation, "
        "verification, and cleanup."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    sub_agents=[
        data_generation_agent,
        business_partner_agent,
        transaction_agent,
        verification_agent,
        cleanup_agent,
    ],
    before_agent_callback=before_agent_callback,
)

# Export for deployment
from vertexai import agent_engines
app = agent_engines.AdkApp(agent=root_agent)
