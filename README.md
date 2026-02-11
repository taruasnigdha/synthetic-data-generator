# 🧪 Synthetic Data Fabricator

> A **Developer Efficiency Agent** built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) that autonomously fabricates realistic synthetic test data in SAP systems.

**Trigger**: A natural-language request for a complex test scenario.
**Result**: The agent plans, generates, executes, and verifies — returning record IDs and confirmation.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     User Prompt                          │
│  "Generate 5 overdue invoices for a US-based customer    │
│   with a credit limit below $5,000"                      │
└──────────────────┬───────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────┐
│          Root Orchestrator Agent (Gemini LLM)            │
│  • Analyzes request                                      │
│  • Plans operation sequence autonomously                 │
│  • Generates realistic data via Faker                    │
│  • Executes SAP API calls                                │
│  • Self-verifies via read-back queries                   │
└──────────────────┬───────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────┐
│              8 Agent Tools                               │
│  generate_synthetic_data │ create_business_partner       │
│  set_credit_limit        │ create_invoice                │
│  adjust_invoice_date     │ create_sales_order            │
│  create_material         │ read_records                  │
└──────────────────┬───────────────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────────────┐
│         Flask Mock SAP Server (localhost:8080)           │
│  SAP-realistic OData endpoints + Web Dashboard UI       │
│  • API_BUSINESS_PARTNER/A_BusinessPartner                │
│  • API_BILLING_DOCUMENT/A_BillingDocument                │
│  • API_SALES_ORDER_SRV/A_SalesOrder                      │
│  • API_PRODUCT_SRV/A_Product                             │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and set your GOOGLE_API_KEY
```

### 3. Run the Mock SAP Server

The mock server simulates SAP S/4HANA OData endpoints locally and provides a web dashboard to view data.

```bash
# Start the mock server standalone
python -m mock_sap_server.app
```

This starts the server at **http://localhost:8080** with:

| URL | Description |
|-----|-------------|
| `http://localhost:8080/` | 📊 **Web Dashboard** — browse all entities with auto-refresh |
| `http://localhost:8080/health` | Health check endpoint |
| `http://localhost:8080/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner` | Business Partner OData API |
| `http://localhost:8080/sap/opu/odata/sap/API_BILLING_DOCUMENT/A_BillingDocument` | Invoice / Billing Document OData API |
| `http://localhost:8080/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder` | Sales Order OData API |
| `http://localhost:8080/sap/opu/odata/sap/API_PRODUCT_SRV/A_Product` | Material / Product OData API |

You can also reset all data at any time:
```bash
curl -X POST http://localhost:8080/admin/reset
```

> **Note:** When using `python run.py`, the mock server starts automatically in the background — no need to start it separately.

### 4. Run the Agent

```bash
# With the default demo prompt
python run.py

# Or with a custom prompt
python run.py "Generate 5 overdue invoices for a US-based customer with a credit limit below \$5,000"
```

### 5. View Results

Open **http://localhost:8080/** to see all created records in the dashboard UI. The dashboard auto-refreshes every 5 seconds.

### 6. Interactive Mode (ADK Web UI)

```bash
# Terminal 1: Start mock server
python -m mock_sap_server.app

# Terminal 2: Launch ADK web UI
adk web .
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | *(required)* | Your Gemini API key |
| `AGENT_MODEL` | `gemini-3-flash-preview` | LLM model for the agent |
| `MOCK_SAP_URL` | `http://localhost:8080` | Mock SAP server URL |

---

## 🧪 Example Test Scenarios

The agent is **fully agentic** — it autonomously decides the workflow for each scenario:

### Scenario 1: Overdue Invoices
```
Generate 5 overdue invoices for a US-based customer with a credit limit below $5,000
```
**Agent decides**: Create BP → Set credit limit → Generate invoice data → Create 5 invoices with past due dates → Verify overdue status

### Scenario 2: Supplier with Sales Orders
```
Create a German supplier with 3 open sales orders, each with 2 line items of different materials
```
**Agent decides**: Generate material data → Create 6 materials → Create BP (supplier type, DE) → Create 3 SOs with 2 items each → Verify

### Scenario 3: Mixed-Status Customers
```
Set up 3 US customers: one with paid invoices, one with overdue invoices, and one with no invoices
```
**Agent decides**: Create 3 BPs → Create paid invoices for BP1 → Create backdated unpaid invoices for BP2 → Skip BP3 → Verify statuses differ

### Scenario 4: Product Catalog + Order
```
Create a product catalog of 10 materials with realistic SKUs and prices, then create a sales order referencing 3 of them
```
**Agent decides**: Generate 10 material records → Create all materials → Create BP → Create SO with 3 line items → Verify

### Scenario 5: Credit Limit Stress Test
```
Generate a customer with credit limit $10,000, 2 paid invoices totaling $8,000, and 1 overdue invoice of $3,000
```
**Agent decides**: Create BP → Set credit limit $10K → Create 2 paid invoices ($4K each) → Create 1 overdue invoice ($3K, past date) → Verify amounts and statuses

---

## 📁 Project Structure

```
synthetic-data-fabricator/
├── .env.example                    # Environment variables template
├── pyproject.toml                  # Python project config
├── README.md                       # This file
├── run.py                          # CLI entry point
├── mock_sap_server/
│   ├── __init__.py
│   ├── app.py                      # Flask SAP OData mock server
│   └── templates/
│       └── dashboard.html          # Web dashboard UI
└── synthetic_data_agent/
    ├── __init__.py                  # Exports root_agent for ADK
    ├── agent.py                     # Agent definition + system prompt
    └── tools.py                     # 8 tool functions
```

---

## 🔒 Safety & Best Practices

- **No real SAP connection** — Uses a local mock server; zero risk to production systems
- **No real data** — All data is synthetically generated via Faker
- **Configurable model** — Switch models via environment variable
- **Self-verification** — Agent always reads back created records to confirm correctness
- **Idempotent mock server** — Reset via `POST /admin/reset` endpoint

---

## 🛠️ Definition of Done

For each scenario, the agent must:

1. ✅ **Plan** — Determine the correct sequence of API calls
2. ✅ **Generate** — Create realistic synthetic data (names, addresses, SKUs)
3. ✅ **Execute** — Commit data to the mock SAP server
4. ✅ **Verify** — Read back records and confirm attributes (Status = 'Overdue', credit limits, etc.)
5. ✅ **Report** — Provide all created record IDs and verification results
