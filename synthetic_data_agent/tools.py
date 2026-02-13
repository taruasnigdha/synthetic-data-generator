"""
Agent Tools for the Synthetic Data Fabricator
==============================================
Each function is a tool the ADK agent can call to interact with the
mock SAP OData server.  Docstrings are critical — the LLM uses them
to understand what tools do and when to call them.
"""

import os
import json
import requests
from faker import Faker
from datetime import datetime, timedelta

MOCK_SAP_URL = os.getenv("MOCK_SAP_URL", "http://localhost:8080")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _url(path: str) -> str:
    return f"{MOCK_SAP_URL}{path}"


def _safe_request(method: str, path: str, **kwargs) -> dict:
    """Execute an HTTP request with structured error handling.

    Returns the parsed JSON on success, or a structured error dict
    that the agent can reason about and recover from.
    """
    kwargs.setdefault("timeout", 10)
    try:
        resp = getattr(requests, method)(_url(path), **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        return {"status": "error", "message": f"Request to {path} timed out after {kwargs['timeout']}s. Retry or check the server."}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": f"Cannot connect to SAP server at {MOCK_SAP_URL}. Is the mock server running?"}
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("error", {}).get("message", e.response.text[:200])
        except Exception:
            detail = e.response.text[:200] if e.response.text else str(e)
        return {"status": "error", "message": f"SAP API error ({e.response.status_code}): {detail}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)[:200]}"}


def _post(path: str, data: dict) -> dict:
    return _safe_request("post", path, json=data)


def _patch(path: str, data: dict) -> dict:
    return _safe_request("patch", path, json=data)


def _get(path: str, params: dict | None = None) -> dict:
    return _safe_request("get", path, params=params or {})


def _delete(path: str) -> dict:
    return _safe_request("delete", path)


# ---------------------------------------------------------------------------
# Tool 1 — Generate Synthetic Data
# ---------------------------------------------------------------------------

def generate_synthetic_data(
    entity_type: str,
    country: str = "US",
    count: int = 1,
) -> dict:
    """Generate realistic synthetic data for SAP entities using the Faker library.

    Use this tool FIRST to create realistic names, addresses, product names,
    and amounts before calling the creation tools.

    Args:
        entity_type: The type of entity to generate data for.
            Must be one of: 'customer', 'supplier', 'invoice', 'sales_order', 'material'.
        country: ISO country code for locale-specific data (e.g. 'US', 'DE', 'IN', 'JP').
        count: Number of records to generate (1-50).

    Returns:
        A dict with key 'records' containing a list of generated data dicts.
        Each dict has fields appropriate for the entity_type.
    """
    locale_map = {
        "US": "en_US", "DE": "de_DE", "IN": "en_IN", "JP": "ja_JP",
        "FR": "fr_FR", "GB": "en_GB", "BR": "pt_BR", "CN": "zh_CN",
        "IT": "it_IT", "ES": "es_ES", "NL": "nl_NL", "AU": "en_AU",
    }
    locale = locale_map.get(country.upper(), "en_US")
    fake = Faker(locale)
    count = max(1, min(count, 50))
    records = []

    for _ in range(count):
        if entity_type.lower() in ("customer", "supplier"):
            records.append({
                "name": fake.company(),
                "country": country.upper(),
                "city": fake.city(),
                "street": fake.street_address(),
                "postal_code": fake.postcode(),
                "region": fake.state() if hasattr(fake, "state") else "",
                "partner_type": entity_type.capitalize(),
            })
        elif entity_type.lower() == "invoice":
            records.append({
                "amount": round(fake.pyfloat(min_value=100, max_value=50000, right_digits=2), 2),
                "currency": "USD" if country.upper() == "US" else "EUR",
                "description": fake.catch_phrase(),
            })
        elif entity_type.lower() == "sales_order":
            records.append({
                "delivery_date": fake.future_date(end_date="+60d").isoformat(),
                "amount": round(fake.pyfloat(min_value=500, max_value=100000, right_digits=2), 2),
                "currency": "USD" if country.upper() == "US" else "EUR",
            })
        elif entity_type.lower() == "material":
            sku = fake.bothify(text="MAT-####-??").upper()
            records.append({
                "name": f"{fake.word().capitalize()} {fake.word().capitalize()} {fake.random_element(['Widget', 'Component', 'Assembly', 'Module', 'Unit', 'Sensor', 'Connector', 'Bracket'])}",
                "sku": sku,
                "material_type": fake.random_element(["FERT", "HALB", "ROH", "HAWA"]),
                "unit": fake.random_element(["EA", "KG", "L", "M", "PC"]),
                "price": round(fake.pyfloat(min_value=5, max_value=5000, right_digits=2), 2),
                "product_group": fake.random_element(["Electronics", "Mechanical", "Raw Materials", "Packaging", "Chemicals"]),
            })
        else:
            records.append({"error": f"Unknown entity_type: {entity_type}"})

    return {"entity_type": entity_type, "country": country, "count": len(records), "records": records}


# ---------------------------------------------------------------------------
# Tool 2 — Create Business Partner
# ---------------------------------------------------------------------------

def create_business_partner(
    name: str,
    country: str,
    city: str,
    street: str,
    postal_code: str,
    partner_type: str = "Customer",
    region: str = "",
    credit_limit: float = 0.0,
    currency: str = "USD",
    email: str = "devstar3372@gcplab.me",
) -> dict:
    """Create a new Business Partner in the SAP system.

    A Business Partner is either a Customer or Supplier in SAP.
    This must be created BEFORE creating invoices or sales orders.

    Args:
        name: The business partner's company or person name.
        country: ISO country code (e.g. 'US', 'DE').
        city: City name.
        street: Street address.
        postal_code: Postal / ZIP code.
        partner_type: Either 'Customer' or 'Supplier'. Defaults to 'Customer'.
        region: State or region (optional).
        credit_limit: Initial credit limit. Can also be set later with set_credit_limit. Defaults to 0.
        currency: Currency code for the credit limit. Defaults to 'USD'.
        email: Contact email address for the business partner. REQUIRED for receiving reminder notifications.
            Defaults to 'devstar3372@gcplab.me' for testing.

    Returns:
        Dict containing the created Business Partner record with its SAP ID.
    """
    payload = {
        "BusinessPartnerName": name,
        "BusinessPartnerType": partner_type,
        "Country": country,
        "City": city,
        "StreetName": street,
        "PostalCode": postal_code,
        "Region": region,
        "CreditLimit": credit_limit,
        "Currency": currency,
        "Email": email,
    }
    result = _post("/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner", payload)
    bp = result.get("d", result)
    return {
        "status": "success",
        "message": f"Business Partner created successfully",
        "BusinessPartner": bp.get("BusinessPartner"),
        "BusinessPartnerName": bp.get("BusinessPartnerName"),
        "CreditLimit": bp.get("CreditLimit"),
    }


# ---------------------------------------------------------------------------
# Tool 3 — Set Credit Limit
# ---------------------------------------------------------------------------

def set_credit_limit(
    partner_id: str,
    credit_limit: float,
    currency: str = "USD",
) -> dict:
    """Set or update the credit limit for an existing Business Partner.

    Args:
        partner_id: The SAP Business Partner ID (e.g. 'BP0000000001').
        credit_limit: The new credit limit amount.
        currency: Currency code (default 'USD').

    Returns:
        Dict confirming the updated credit limit.
    """
    payload = {"CreditLimit": credit_limit, "Currency": currency}
    result = _patch(
        f"/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner('{partner_id}')",
        payload,
    )
    bp = result.get("d", result)
    return {
        "status": "success",
        "message": f"Credit limit updated for {partner_id}",
        "BusinessPartner": partner_id,
        "CreditLimit": bp.get("CreditLimit"),
        "Currency": bp.get("Currency"),
    }


# ---------------------------------------------------------------------------
# Tool 4 — Create Invoice (Billing Document)
# ---------------------------------------------------------------------------

def create_invoice(
    partner_id: str,
    amount: float,
    currency: str = "USD",
    due_date: str = "",
    payment_status: str = "Unpaid",
    line_items_json: str = "[]",
) -> dict:
    """Create a new Invoice (Billing Document) in the SAP system.

    The Business Partner must already exist.  If the due_date is in the past
    and payment_status is 'Unpaid', the invoice will automatically be marked
    as 'Overdue' by the system.

    Args:
        partner_id: The SAP Business Partner ID to bill.
        amount: Total invoice amount.
        currency: Currency code (default 'USD').
        due_date: Due date in ISO format (YYYY-MM-DD).  Leave empty for today.
            Set to a past date to create an overdue invoice.
        payment_status: Either 'Unpaid' or 'Paid'.  Defaults to 'Unpaid'.
        line_items_json: Optional JSON string of line items array.  Each item
            should have keys: 'description', 'quantity', 'unit_price'.
            Example: '[{"description": "Widget", "quantity": 5, "unit_price": 100}]'
            Defaults to empty array '[]'.

    Returns:
        Dict containing the created Invoice record with its document ID and status.
    """
    try:
        line_items = json.loads(line_items_json) if line_items_json else []
    except (json.JSONDecodeError, TypeError):
        line_items = []
    payload = {
        "BusinessPartner": partner_id,
        "TotalNetAmount": amount,
        "TransactionCurrency": currency,
        "DueDate": due_date,
        "PaymentStatus": payment_status,
        "LineItems": line_items,
    }
    result = _post(
        "/sap/opu/odata/sap/API_BILLING_DOCUMENT/A_BillingDocument",
        payload,
    )
    inv = result.get("d", result)
    return {
        "status": "success",
        "message": f"Invoice created successfully",
        "BillingDocument": inv.get("BillingDocument"),
        "BusinessPartner": partner_id,
        "TotalNetAmount": inv.get("TotalNetAmount"),
        "DueDate": inv.get("DueDate"),
        "InvoiceStatus": inv.get("Status"),
    }


# ---------------------------------------------------------------------------
# Tool 5 — Adjust Invoice Date
# ---------------------------------------------------------------------------

def adjust_invoice_date(
    invoice_id: str,
    new_due_date: str,
) -> dict:
    """Change the due date of an existing invoice.

    Use this to backdate an invoice to a past date, which will cause the
    system to automatically mark it as 'Overdue' if the payment status is 'Unpaid'.

    Args:
        invoice_id: The SAP Billing Document ID (e.g. 'INV1A2B3C4D').
        new_due_date: The new due date in ISO format (YYYY-MM-DD).
            Use a past date to make the invoice overdue.

    Returns:
        Dict with the updated invoice status.
    """
    payload = {"DueDate": new_due_date}
    result = _patch(
        f"/sap/opu/odata/sap/API_BILLING_DOCUMENT/A_BillingDocument('{invoice_id}')",
        payload,
    )
    inv = result.get("d", result)
    return {
        "status": "success",
        "message": f"Invoice {invoice_id} due date updated to {new_due_date}",
        "BillingDocument": invoice_id,
        "DueDate": inv.get("DueDate"),
        "InvoiceStatus": inv.get("Status"),
    }


# ---------------------------------------------------------------------------
# Tool 6 — Create Sales Order
# ---------------------------------------------------------------------------

def create_sales_order(
    partner_id: str,
    items_json: str,
    requested_delivery_date: str = "",
    total_amount: float = 0.0,
    currency: str = "USD",
    sales_order_type: str = "OR",
) -> dict:
    """Create a new Sales Order in the SAP system.

    The Business Partner must already exist.  If referencing materials,
    create the materials first.

    Args:
        partner_id: The SAP Business Partner ID.
        items_json: JSON string of line items array.  Each item should have keys:
            'material_id' (optional), 'description', 'quantity', 'unit_price'.
            Example: '[{"description": "Widget Pro", "quantity": 10, "unit_price": 29.99, "material_id": "MAT1A2B3C4D"}]'
        requested_delivery_date: Requested delivery date (YYYY-MM-DD). Optional.
        total_amount: Total order amount. If 0, will be computed from items.
        currency: Currency code (default 'USD').
        sales_order_type: SAP order type (default 'OR' = Standard Order).

    Returns:
        Dict with the created Sales Order record and its ID.
    """
    try:
        items = json.loads(items_json) if items_json else []
    except (json.JSONDecodeError, TypeError):
        items = []
    if total_amount == 0 and items:
        total_amount = sum(
            item.get("quantity", 1) * item.get("unit_price", 0) for item in items
        )
    payload = {
        "BusinessPartner": partner_id,
        "SalesOrderType": sales_order_type,
        "RequestedDeliveryDate": requested_delivery_date,
        "TotalNetAmount": round(total_amount, 2),
        "TransactionCurrency": currency,
        "LineItems": items,
    }
    result = _post(
        "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder",
        payload,
    )
    so = result.get("d", result)
    return {
        "status": "success",
        "message": "Sales Order created successfully",
        "SalesOrder": so.get("SalesOrder"),
        "BusinessPartner": partner_id,
        "TotalNetAmount": so.get("TotalNetAmount"),
        "ItemCount": len(items),
    }


# ---------------------------------------------------------------------------
# Tool 7 — Create Material / Product
# ---------------------------------------------------------------------------

def create_material(
    name: str,
    material_type: str = "FERT",
    unit: str = "EA",
    price: float = 0.0,
    currency: str = "USD",
    product_group: str = "",
) -> dict:
    """Create a new Material (Product) in the SAP system.

    Materials should be created BEFORE referencing them in Sales Orders.

    Args:
        name: Product name / description.
        material_type: SAP material type. Common values:
            'FERT' (Finished Good), 'HALB' (Semifinished),
            'ROH' (Raw Material), 'HAWA' (Trading Goods).
        unit: Base unit of measure. Common values: 'EA' (Each), 'KG', 'L', 'M', 'PC'.
        price: Standard price per unit.
        currency: Currency code (default 'USD').
        product_group: Product group / category (optional).

    Returns:
        Dict with the created Material record and its ID.
    """
    payload = {
        "ProductName": name,
        "ProductType": material_type,
        "BaseUnit": unit,
        "StandardPrice": price,
        "Currency": currency,
        "ProductGroup": product_group,
    }
    result = _post(
        "/sap/opu/odata/sap/API_PRODUCT_SRV/A_Product",
        payload,
    )
    mat = result.get("d", result)
    return {
        "status": "success",
        "message": f"Material created successfully",
        "Product": mat.get("Product"),
        "ProductName": mat.get("ProductName"),
        "StandardPrice": mat.get("StandardPrice"),
    }


# ---------------------------------------------------------------------------
# Tool 8 — Read / Verify Records
# ---------------------------------------------------------------------------

def read_records(
    entity_type: str,
    filter_expression: str = "",
) -> dict:
    """Read records from the SAP system with optional OData filtering.

    Use this to VERIFY that records were created correctly.
    Call this AFTER creating records to confirm their attributes.

    Args:
        entity_type: The entity to query.  Must be one of:
            'BusinessPartner', 'Invoice', 'SalesOrder', 'Material'.
        filter_expression: Optional OData $filter expression.
            Examples:
            - "BusinessPartner eq 'BP0000000001'"
            - "Status eq 'Overdue'"
            - "Country eq 'US'"
            - "BusinessPartner eq 'BP0000000001' and Status eq 'Overdue'"
            Leave empty to return all records of the type.

    Returns:
        Dict with 'count' and 'records' list.
    """
    path_map = {
        "BusinessPartner": "/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner",
        "Invoice": "/sap/opu/odata/sap/API_BILLING_DOCUMENT/A_BillingDocument",
        "SalesOrder": "/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder",
        "Material": "/sap/opu/odata/sap/API_PRODUCT_SRV/A_Product",
    }
    path = path_map.get(entity_type)
    if not path:
        return {"error": f"Unknown entity_type '{entity_type}'. Use one of: {list(path_map.keys())}"}

    params = {}
    if filter_expression:
        params["$filter"] = filter_expression

    result = _get(path, params)
    if result.get("status") == "error":
        return result
    records = result.get("d", {}).get("results", [])
    return {
        "entity_type": entity_type,
        "filter": filter_expression or "(none)",
        "count": len(records),
        "records": records,
    }


# ---------------------------------------------------------------------------
# Path map shared by read/delete tools
# ---------------------------------------------------------------------------
_ENTITY_PATH_MAP = {
    "BusinessPartner": ("/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner", "BusinessPartner"),
    "Invoice": ("/sap/opu/odata/sap/API_BILLING_DOCUMENT/A_BillingDocument", "BillingDocument"),
    "SalesOrder": ("/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrder", "SalesOrder"),
    "Material": ("/sap/opu/odata/sap/API_PRODUCT_SRV/A_Product", "Product"),
}


# ---------------------------------------------------------------------------
# Tool 9 — Delete a Single Record
# ---------------------------------------------------------------------------

def delete_record(
    entity_type: str,
    record_id: str,
) -> dict:
    """Delete a single record from the SAP system.

    Use this to remove records the user doesn't want, e.g. if they
    don't like the generated data and want to regenerate it.

    IMPORTANT: This is a destructive operation — the agent will ask
    for user confirmation before this tool executes.

    Args:
        entity_type: The entity to delete from. Must be one of:
            'BusinessPartner', 'Invoice', 'SalesOrder', 'Material'.
        record_id: The ID of the record to delete
            (e.g. 'BP0000000001', 'INV1A2B3C4D', 'SO1A2B3C4D', 'MAT1A2B3C4D').

    Returns:
        Dict confirming the deletion or an error message.
    """
    entry = _ENTITY_PATH_MAP.get(entity_type)
    if not entry:
        return {"status": "error", "message": f"Unknown entity_type '{entity_type}'. Use one of: {list(_ENTITY_PATH_MAP.keys())}"}

    path, _ = entry
    result = _delete(f"{path}('{record_id}')")
    if result.get("status") == "error":
        return result
    return {
        "status": "success",
        "message": f"Deleted {entity_type} record '{record_id}'",
        "entity_type": entity_type,
        "record_id": record_id,
    }


# ---------------------------------------------------------------------------
# Tool 10 — Delete Records by Filter
# ---------------------------------------------------------------------------

def delete_by_filter(
    entity_type: str,
    filter_expression: str = "",
) -> dict:
    """Delete multiple records matching a filter from the SAP system.

    Use this to bulk-delete records, e.g. "delete all overdue invoices"
    or "delete all invoices for partner BP0000000001".

    IMPORTANT: This is a destructive operation — the agent will ask
    for user confirmation before this tool executes.

    Args:
        entity_type: The entity type to delete from. Must be one of:
            'BusinessPartner', 'Invoice', 'SalesOrder', 'Material'.
        filter_expression: Optional OData $filter expression to select records.
            Examples:
            - "BusinessPartner eq 'BP0000000001'"
            - "Status eq 'Overdue'"
            Leave empty to delete ALL records of this type.

    Returns:
        Dict with the count and IDs of deleted records.
    """
    if entity_type not in _ENTITY_PATH_MAP:
        return {"status": "error", "message": f"Unknown entity_type '{entity_type}'. Use one of: {list(_ENTITY_PATH_MAP.keys())}"}

    payload = {"entity_type": entity_type, "filter": filter_expression}
    result = _post("/admin/bulk-delete", payload)
    if result.get("status") == "error":
        return result
    return {
        "status": "success",
        "message": result.get("message", "Records deleted"),
        "deleted_count": result.get("deleted_count", 0),
        "deleted_ids": result.get("deleted_ids", []),
    }


# ---------------------------------------------------------------------------
# Tool 11 — Reset All Data
# ---------------------------------------------------------------------------

def reset_all_data() -> dict:
    """Reset ALL data in the SAP system — removes every record of every type.

    This is the nuclear option. Only use when the user explicitly asks
    to start fresh or clear everything.

    IMPORTANT: This is a destructive operation — the agent will ask
    for user confirmation before this tool executes.

    This deletes ALL Business Partners, Invoices, Sales Orders,
    and Materials. This cannot be undone.

    Returns:
        Dict confirming the reset.
    """
    result = _post("/admin/reset", {})
    if result.get("status") == "error":
        return result
    return {
        "status": "success",
        "message": "All SAP data has been reset. The system is now empty.",
    }


# ---------------------------------------------------------------------------
# Tool 12 — Create Reminder
# ---------------------------------------------------------------------------

def create_reminder(
    reminder_type: str,
    entity_id: str,
    entity_type: str,
    message: str,
    trigger_date: str = "",
    priority: str = "medium",
    recurring: str = "no",
) -> dict:
    """Create a reminder for an invoice, sales order, or business partner.

    Use this to set up automated reminders for overdue invoices, upcoming due dates,
    credit limit warnings, delivery deadlines, or any other time-sensitive events.

    Args:
        reminder_type: Type of reminder. Must be one of:
            'overdue_invoice' - Reminder for overdue payment
            'upcoming_due_date' - Reminder for invoice due soon (7 days before)
            'credit_limit_warning' - Warning when approaching credit limit
            'delivery_reminder' - Reminder for upcoming delivery
            'custom' - Custom reminder message
        entity_id: The SAP record ID this reminder relates to
            (e.g. 'BP0000000001', 'INV1A2B3C4D', 'SO1A2B3C4D').
        entity_type: The entity type. Must be one of:
            'BusinessPartner', 'Invoice', 'SalesOrder'.
        message: The reminder message text to display.
        trigger_date: When to trigger the reminder in ISO format (YYYY-MM-DD).
            Leave empty to trigger immediately for overdue items.
            For 'upcoming_due_date', this is auto-calculated as 7 days before due date.
        priority: Reminder priority. Must be one of: 'low', 'medium', 'high', 'critical'.
            Defaults to 'medium'.
        recurring: Whether this reminder repeats. Must be one of:
            'no' (one-time), 'daily', 'weekly', 'monthly'.
            Defaults to 'no'.

    Returns:
        Dict with the created reminder ID and details.
    """
    # Auto-calculate trigger date for overdue reminders
    if not trigger_date and reminder_type == "overdue_invoice":
        trigger_date = datetime.now().strftime("%Y-%m-%d")
    
    payload = {
        "ReminderType": reminder_type,
        "EntityID": entity_id,
        "EntityType": entity_type,
        "Message": message,
        "TriggerDate": trigger_date,
        "Priority": priority,
        "Recurring": recurring,
        "Status": "active",
    }
    
    result = _post("/api/reminders", payload)
    reminder = result.get("d", result)
    
    return {
        "status": "success",
        "message": f"Reminder created successfully for {entity_type} {entity_id}",
        "ReminderID": reminder.get("ReminderID"),
        "EntityID": entity_id,
        "EntityType": entity_type,
        "TriggerDate": trigger_date,
        "Priority": priority,
    }


# ---------------------------------------------------------------------------
# Tool 13 — List Active Reminders
# ---------------------------------------------------------------------------

def list_reminders(
    entity_type: str = "",
    entity_id: str = "",
    priority: str = "",
    status: str = "active",
) -> dict:
    """List all reminders, optionally filtered by entity, priority, or status.

    Use this to view all active reminders, check reminders for a specific
    entity, or find high-priority reminders that need attention.

    Args:
        entity_type: Optional filter by entity type
            ('BusinessPartner', 'Invoice', 'SalesOrder').
            Leave empty to see all reminders.
        entity_id: Optional filter by specific entity ID
            (e.g. 'BP0000000001', 'INV1A2B3C4D').
            Leave empty to see all reminders.
        priority: Optional filter by priority
            ('low', 'medium', 'high', 'critical').
            Leave empty to see all priorities.
        status: Filter by reminder status.
            'active' (default) - Active reminders
            'completed' - Dismissed/completed reminders
            'all' - All reminders regardless of status

    Returns:
        Dict with count and list of reminders matching the filters.
    """
    params = {}
    if entity_type:
        params["entity_type"] = entity_type
    if entity_id:
        params["entity_id"] = entity_id
    if priority:
        params["priority"] = priority
    if status and status != "all":
        params["status"] = status
    
    result = _get("/api/reminders", params)
    if result.get("status") == "error":
        return result
    
    reminders = result.get("reminders", [])
    
    return {
        "status": "success",
        "count": len(reminders),
        "filters": params,
        "reminders": reminders,
    }


# ---------------------------------------------------------------------------
# Tool 14 — Check Due Soon Invoices
# ---------------------------------------------------------------------------

def check_due_soon(
    days_ahead: int = 7,
    auto_create_reminders: bool = False,
) -> dict:
    """Check for invoices that will be due soon and optionally create reminders.

    Use this to proactively identify invoices approaching their due dates
    so payment can be arranged in time.

    Args:
        days_ahead: How many days ahead to check. Defaults to 7 days.
            For example, days_ahead=7 finds all unpaid invoices due within the next 7 days.
        auto_create_reminders: If True, automatically create reminders for invoices
            found due soon. Defaults to False (just report, don't create reminders).

    Returns:
        Dict with count of invoices due soon, their details, and reminder IDs if created.
    """
    today = datetime.now()
    future_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    # Query for unpaid invoices due within the date range
    filter_expr = f"PaymentStatus eq 'Unpaid' and DueDate ge '{today_str}' and DueDate le '{future_date}'"
    result = read_records("Invoice", filter_expr)
    
    if result.get("error") or result.get("status") == "error":
        return result
    
    invoices = result.get("records", [])
    created_reminders = []
    
    if auto_create_reminders and invoices:
        for inv in invoices:
            inv_id = inv.get("BillingDocument")
            due_date = inv.get("DueDate")
            partner = inv.get("BusinessPartner")
            amount = inv.get("TotalNetAmount")
            
            message = f"Invoice {inv_id} for ${amount} due on {due_date}. Partner: {partner}"
            
            reminder_result = create_reminder(
                reminder_type="upcoming_due_date",
                entity_id=inv_id,
                entity_type="Invoice",
                message=message,
                trigger_date=due_date,
                priority="medium",
            )
            
            if reminder_result.get("status") == "success":
                created_reminders.append(reminder_result.get("ReminderID"))
    
    return {
        "status": "success",
        "days_ahead": days_ahead,
        "count": len(invoices),
        "invoices_due_soon": invoices,
        "reminders_created": len(created_reminders),
        "reminder_ids": created_reminders,
    }


# ---------------------------------------------------------------------------
# Tool 15 — Dismiss Reminder
# ---------------------------------------------------------------------------

def dismiss_reminder(
    reminder_id: str,
) -> dict:
    """Dismiss or mark a reminder as completed.

    Use this when the reminder has been acted upon or is no longer needed.

    Args:
        reminder_id: The reminder ID to dismiss (e.g. 'REM1A2B3C4D').

    Returns:
        Dict confirming the reminder was dismissed.
    """
    result = _patch(f"/api/reminders/{reminder_id}", {"Status": "completed"})
    
    if result.get("status") == "error":
        return result
    
    return {
        "status": "success",
        "message": f"Reminder {reminder_id} has been dismissed",
        "ReminderID": reminder_id,
    }


# ---------------------------------------------------------------------------
# Email Helper Functions
# ---------------------------------------------------------------------------

def _get_email_template(reminder_type: str, data: dict) -> tuple[str, str]:
    """Generate HTML email template based on reminder type.
    
    Returns:
        Tuple of (subject, html_body)
    """
    invoice_id = data.get("invoice_id", "N/A")
    amount = data.get("amount", "0.00")
    currency = data.get("currency", "USD")
    due_date = data.get("due_date", "N/A")
    partner_name = data.get("partner_name", "Valued Customer")
    days_until_due = data.get("days_until_due", 0)
    
    if reminder_type == "overdue_invoice":
        subject = f"⚠️ Overdue Invoice {invoice_id} - Immediate Action Required"
        priority_color = "#dc3545"  # Red
        priority_text = "OVERDUE - URGENT"
        message = f"This invoice is now overdue. Please arrange payment immediately to avoid any service interruptions."
    elif reminder_type == "upcoming_due_date":
        subject = f"📅 Payment Reminder: Invoice {invoice_id} Due Soon"
        priority_color = "#ffc107"  # Yellow/Orange
        priority_text = f"DUE IN {abs(days_until_due)} DAYS"
        message = f"This invoice will be due on {due_date}. Please arrange payment to avoid late fees."
    else:
        subject = f"🔔 Reminder: Invoice {invoice_id}"
        priority_color = "#17a2b8"  # Blue
        priority_text = "REMINDER"
        message = data.get("message", "Please review this invoice.")
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .header {{
                background: {priority_color};
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .priority-badge {{
                background: rgba(255,255,255,0.2);
                padding: 5px 15px;
                border-radius: 20px;
                display: inline-block;
                margin-top: 10px;
                font-size: 12px;
                font-weight: bold;
            }}
            .content {{
                padding: 30px 20px;
            }}
            .invoice-details {{
                background: #f8f9fa;
                border-left: 4px solid {priority_color};
                padding: 20px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #dee2e6;
            }}
            .detail-row:last-child {{
                border-bottom: none;
            }}
            .detail-label {{
                font-weight: bold;
                color: #6c757d;
            }}
            .detail-value {{
                color: #333;
                font-weight: 600;
            }}
            .amount {{
                font-size: 28px;
                color: {priority_color};
                font-weight: bold;
            }}
            .message-box {{
                background: #e9ecef;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .footer {{
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #6c757d;
                border-top: 1px solid #dee2e6;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background: {priority_color};
                color: #ffffff;
                text-decoration: none;
                border-radius: 4px;
                margin: 20px 0;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>💼 SAP Invoice Reminder</h1>
                <div class="priority-badge">{priority_text}</div>
            </div>
            
            <div class="content">
                <p>Dear {partner_name},</p>
                
                <div class="message-box">
                    <p><strong>{message}</strong></p>
                </div>
                
                <div class="invoice-details">
                    <div class="detail-row">
                        <span class="detail-label">Invoice Number:</span>
                        <span class="detail-value">{invoice_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Due Date:</span>
                        <span class="detail-value">{due_date}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Amount Due:</span>
                        <span class="detail-value amount">{currency} {amount:,.2f}</span>
                    </div>
                </div>
                
                <p>If you have already processed this payment, please disregard this reminder.</p>
                
                <p>For any questions or concerns, please contact our accounts team.</p>
                
                <p>Best regards,<br>
                <strong>SAP Reminder System</strong></p>
            </div>
            
            <div class="footer">
                <p>This is an automated reminder from SAP Synthetic Data Fabricator</p>
                <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, html_body


def _send_email_smtp(to_email: str, subject: str, html_body: str) -> dict:
    """Send email using SMTP.
    
    Returns:
        Dict with status and message.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)
        from_name = os.getenv("SMTP_FROM_NAME", "SAP Reminder System")
        
        if not smtp_user or not smtp_password:
            return {
                "status": "error",
                "message": "SMTP credentials not configured. Please set SMTP_USER and SMTP_PASSWORD in .env file."
            }
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        
        # Attach HTML body
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        return {
            "status": "success",
            "message": f"Email sent successfully to {to_email}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}"
        }


# ---------------------------------------------------------------------------
# Tool 16 — Send Reminder Email
# ---------------------------------------------------------------------------

def send_reminder_email(
    invoice_id: str,
    partner_id: str,
    reminder_type: str = "upcoming_due_date",
) -> dict:
    """Send an email reminder for an invoice to the associated Business Partner.
    
    This tool:
    1. Retrieves invoice details (amount, due date, status)
    2. Retrieves Business Partner email address
    3. Generates HTML email from template
    4. Sends email via SMTP
    
    Use this after creating a reminder to actually notify the customer via email.
    
    Args:
        invoice_id: The SAP Billing Document ID (e.g. 'INV1A2B3C4D').
        partner_id: The Business Partner ID (e.g. 'BP0000000001').
        reminder_type: Type of reminder email. Must be one of:
            'overdue_invoice' - Urgent, for past-due invoices
            'upcoming_due_date' - Standard reminder for invoices due soon
            'custom' - Generic reminder
            Defaults to 'upcoming_due_date'.
    
    Returns:
        Dict with email send status, recipient email, and delivery details.
    """
    # Get invoice details
    invoice_result = read_records("Invoice", f"BillingDocument eq '{invoice_id}'")
    if invoice_result.get("error") or invoice_result.get("count", 0) == 0:
        return {
            "status": "error",
            "message": f"Invoice {invoice_id} not found"
        }
    
    invoice = invoice_result["records"][0]
    
    # Get Business Partner details (to get email)
    bp_result = read_records("BusinessPartner", f"BusinessPartner eq '{partner_id}'")
    if bp_result.get("error") or bp_result.get("count", 0) == 0:
        return {
            "status": "error",
            "message": f"Business Partner {partner_id} not found"
        }
    
    partner = bp_result["records"][0]
    partner_email = partner.get("Email", "")
    
    if not partner_email:
        return {
            "status": "error",
            "message": f"No email address found for Business Partner {partner_id}. Email is required for notifications."
        }
    
    # Calculate days until due
    due_date_str = invoice.get("DueDate", "")
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        days_until_due = (due_date - datetime.now()).days
    except:
        days_until_due = 0
    
    # Prepare email data
    email_data = {
        "invoice_id": invoice_id,
        "amount": invoice.get("TotalNetAmount", 0),
        "currency": invoice.get("TransactionCurrency", "USD"),
        "due_date": due_date_str,
        "partner_name": partner.get("BusinessPartnerName", "Valued Customer"),
        "days_until_due": days_until_due,
        "message": f"Invoice {invoice_id} for {invoice.get('TransactionCurrency', 'USD')} {invoice.get('TotalNetAmount', 0):,.2f} requires your attention."
    }
    
    # Generate email from template
    subject, html_body = _get_email_template(reminder_type, email_data)
    
    # Send email
    send_result = _send_email_smtp(partner_email, subject, html_body)
    
    if send_result.get("status") == "success":
        return {
            "status": "success",
            "message": f"Reminder email sent successfully",
            "recipient_email": partner_email,
            "invoice_id": invoice_id,
            "partner_id": partner_id,
            "subject": subject,
            "days_until_due": days_until_due,
        }
    else:
        return {
            "status": "error",
            "message": send_result.get("message", "Failed to send email"),
            "recipient_email": partner_email,
        }


# ---------------------------------------------------------------------------
# Tool 17 — Check Due Soon and Send Email Reminders
# ---------------------------------------------------------------------------

def check_due_soon_and_email(
    days_ahead: int = 7,
) -> dict:
    """Check for invoices due soon and automatically send email reminders.
    
    This is a convenience tool that combines check_due_soon with automatic
    email notifications. For each invoice found:
    1. Checks if invoice is due within specified days
    2. Creates a reminder record
    3. Sends email notification to Business Partner
    
    Use this for automated daily/weekly reminder workflows.
    
    Args:
        days_ahead: How many days ahead to check. Defaults to 7 days.
            For example, days_ahead=7 finds all unpaid invoices due within the next 7 days.
    
    Returns:
        Dict with count of invoices found, emails sent, and detailed results.
    """
    today = datetime.now()
    future_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    # Query for unpaid invoices due within the date range
    filter_expr = f"PaymentStatus eq 'Unpaid' and DueDate ge '{today_str}' and DueDate le '{future_date}'"
    result = read_records("Invoice", filter_expr)
    
    if result.get("error") or result.get("status") == "error":
        return result
    
    invoices = result.get("records", [])
    
    email_results = []
    reminders_created = []
    emails_sent = 0
    emails_failed = 0
    
    for inv in invoices:
        inv_id = inv.get("BillingDocument")
        due_date = inv.get("DueDate")
        partner_id = inv.get("BusinessPartner")
        amount = inv.get("TotalNetAmount")
        
        # Determine reminder type based on days until due
        try:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
            days_until_due = (due_date_obj - today).days
            
            if days_until_due < 0:
                reminder_type = "overdue_invoice"
                priority = "critical"
            elif days_until_due <= 3:
                reminder_type = "upcoming_due_date"
                priority = "high"
            else:
                reminder_type = "upcoming_due_date"
                priority = "medium"
        except:
            reminder_type = "upcoming_due_date"
            priority = "medium"
            days_until_due = 0
        
        # Create reminder
        message = f"Invoice {inv_id} for ${amount} due on {due_date}. Partner: {partner_id}"
        reminder_result = create_reminder(
            reminder_type=reminder_type,
            entity_id=inv_id,
            entity_type="Invoice",
            message=message,
            trigger_date=due_date,
            priority=priority,
        )
        
        if reminder_result.get("status") == "success":
            reminders_created.append(reminder_result.get("ReminderID"))
        
        # Send email
        email_result = send_reminder_email(
            invoice_id=inv_id,
            partner_id=partner_id,
            reminder_type=reminder_type,
        )
        
        if email_result.get("status") == "success":
            emails_sent += 1
        else:
            emails_failed += 1
        
        email_results.append({
            "invoice_id": inv_id,
            "partner_id": partner_id,
            "email_status": email_result.get("status"),
            "recipient_email": email_result.get("recipient_email"),
            "days_until_due": days_until_due,
        })
    
    return {
        "status": "success",
        "days_ahead": days_ahead,
        "invoices_found": len(invoices),
        "reminders_created": len(reminders_created),
        "emails_sent": emails_sent,
        "emails_failed": emails_failed,
        "reminder_ids": reminders_created,
        "email_results": email_results,
    }


# ===========================================================================
# ANALYTICS & REPORTING TOOLS
# ===========================================================================

# ---------------------------------------------------------------------------
# Tool 18 — Get Aging Report
# ---------------------------------------------------------------------------

def get_aging_report() -> dict:
    """Generate an aging report for all unpaid invoices.
    
    Groups unpaid invoices into aging buckets to show how long they've been outstanding.
    This is essential for accounts receivable management and collections prioritization.
    
    Aging Buckets:
    - Current: Not yet due
    - 1-30 days overdue
    - 31-60 days overdue
    - 61-90 days overdue
    - 90+ days overdue (critical)
    
    Returns:
        Dict with aging buckets, counts, and total amounts for each bucket.
    """
    # Get all unpaid invoices
    result = read_records("Invoice", "PaymentStatus eq 'Unpaid'")
    
    if result.get("error") or result.get("status") == "error":
        return result
    
    invoices = result.get("records", [])
    today = datetime.now()
    
    # Initialize aging buckets
    aging_buckets = {
        "current": {"count": 0, "amount": 0, "invoices": []},
        "1-30_days": {"count": 0, "amount": 0, "invoices": []},
        "31-60_days": {"count": 0, "amount": 0, "invoices": []},
        "61-90_days": {"count": 0, "amount": 0, "invoices": []},
        "over_90_days": {"count": 0, "amount": 0, "invoices": []},
    }
    
    for inv in invoices:
        inv_id = inv.get("BillingDocument")
        amount = inv.get("TotalNetAmount", 0)
        due_date_str = inv.get("DueDate", "")
        partner_id = inv.get("BusinessPartner", "")
        
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            days_overdue = (today - due_date).days
            
            inv_summary = {
                "invoice_id": inv_id,
                "partner_id": partner_id,
                "amount": amount,
                "due_date": due_date_str,
                "days_overdue": days_overdue
            }
            
            if days_overdue < 0:
                # Not yet due
                aging_buckets["current"]["count"] += 1
                aging_buckets["current"]["amount"] += amount
                aging_buckets["current"]["invoices"].append(inv_summary)
            elif days_overdue <= 30:
                aging_buckets["1-30_days"]["count"] += 1
                aging_buckets["1-30_days"]["amount"] += amount
                aging_buckets["1-30_days"]["invoices"].append(inv_summary)
            elif days_overdue <= 60:
                aging_buckets["31-60_days"]["count"] += 1
                aging_buckets["31-60_days"]["amount"] += amount
                aging_buckets["31-60_days"]["invoices"].append(inv_summary)
            elif days_overdue <= 90:
                aging_buckets["61-90_days"]["count"] += 1
                aging_buckets["61-90_days"]["amount"] += amount
                aging_buckets["61-90_days"]["invoices"].append(inv_summary)
            else:
                aging_buckets["over_90_days"]["count"] += 1
                aging_buckets["over_90_days"]["amount"] += amount
                aging_buckets["over_90_days"]["invoices"].append(inv_summary)
        except:
            continue
    
    # Calculate totals
    total_count = sum(bucket["count"] for bucket in aging_buckets.values())
    total_amount = sum(bucket["amount"] for bucket in aging_buckets.values())
    
    return {
        "status": "success",
        "report_date": today.strftime("%Y-%m-%d"),
        "total_unpaid_invoices": total_count,
        "total_unpaid_amount": round(total_amount, 2),
        "aging_buckets": {
            "current": {
                "count": aging_buckets["current"]["count"],
                "amount": round(aging_buckets["current"]["amount"], 2),
                "percentage": round(aging_buckets["current"]["amount"] / total_amount * 100, 1) if total_amount > 0 else 0,
                "invoices": aging_buckets["current"]["invoices"]
            },
            "1-30_days_overdue": {
                "count": aging_buckets["1-30_days"]["count"],
                "amount": round(aging_buckets["1-30_days"]["amount"], 2),
                "percentage": round(aging_buckets["1-30_days"]["amount"] / total_amount * 100, 1) if total_amount > 0 else 0,
                "invoices": aging_buckets["1-30_days"]["invoices"]
            },
            "31-60_days_overdue": {
                "count": aging_buckets["31-60_days"]["count"],
                "amount": round(aging_buckets["31-60_days"]["amount"], 2),
                "percentage": round(aging_buckets["31-60_days"]["amount"] / total_amount * 100, 1) if total_amount > 0 else 0,
                "invoices": aging_buckets["31-60_days"]["invoices"]
            },
            "61-90_days_overdue": {
                "count": aging_buckets["61-90_days"]["count"],
                "amount": round(aging_buckets["61-90_days"]["amount"], 2),
                "percentage": round(aging_buckets["61-90_days"]["amount"] / total_amount * 100, 1) if total_amount > 0 else 0,
                "invoices": aging_buckets["61-90_days"]["invoices"]
            },
            "over_90_days_overdue": {
                "count": aging_buckets["over_90_days"]["count"],
                "amount": round(aging_buckets["over_90_days"]["amount"], 2),
                "percentage": round(aging_buckets["over_90_days"]["amount"] / total_amount * 100, 1) if total_amount > 0 else 0,
                "invoices": aging_buckets["over_90_days"]["invoices"]
            }
        }
    }


# ---------------------------------------------------------------------------
# Tool 19 — Calculate KPIs
# ---------------------------------------------------------------------------

def calculate_kpis() -> dict:
    """Calculate key performance indicators (KPIs) for accounts receivable.
    
    Provides high-level metrics for financial health and collections performance:
    - Total outstanding amount (unpaid invoices)
    - Overdue amount and percentage
    - Number of customers with overdue invoices
    - Average invoice amount
    - Overdue rate (percentage of invoices overdue)
    
    Returns:
        Dict with comprehensive KPI metrics.
    """
    # Get all invoices
    all_invoices_result = read_records("Invoice", "")
    invoices = all_invoices_result.get("records", [])
    
    # Get unpaid invoices
    unpaid_result = read_records("Invoice", "PaymentStatus eq 'Unpaid'")
    unpaid_invoices = unpaid_result.get("records", [])
    
    # Get paid invoices
    paid_result = read_records("Invoice", "PaymentStatus eq 'Paid'")
    paid_invoices = paid_result.get("records", [])
    
    # Get overdue invoices
    overdue_result = read_records("Invoice", "Status eq 'Overdue'")
    overdue_invoices = overdue_result.get("records", [])
    
    # Get all business partners
    partners_result = read_records("BusinessPartner", "")
    partners = partners_result.get("records", [])
    
    today = datetime.now()
    
    # Calculate metrics
    total_invoices = len(invoices)
    total_unpaid = len(unpaid_invoices)
    total_paid = len(paid_invoices)
    total_overdue = len(overdue_invoices)
    
    total_unpaid_amount = sum(inv.get("TotalNetAmount", 0) for inv in unpaid_invoices)
    total_overdue_amount = sum(inv.get("TotalNetAmount", 0) for inv in overdue_invoices)
    total_paid_amount = sum(inv.get("TotalNetAmount", 0) for inv in paid_invoices)
    total_revenue = sum(inv.get("TotalNetAmount", 0) for inv in invoices)
    
    # Average invoice amount
    avg_invoice_amount = total_revenue / total_invoices if total_invoices > 0 else 0
    
    # Overdue rate
    overdue_rate = (total_overdue / total_invoices * 100) if total_invoices > 0 else 0
    
    # Customers with overdue invoices
    overdue_partners = set(inv.get("BusinessPartner") for inv in overdue_invoices)
    
    # Collection rate
    collection_rate = (total_paid_amount / total_revenue * 100) if total_revenue > 0 else 0
    
    # Average days overdue for overdue invoices
    days_overdue_list = []
    for inv in overdue_invoices:
        due_date_str = inv.get("DueDate", "")
        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            days_overdue = (today - due_date).days
            days_overdue_list.append(days_overdue)
        except:
            continue
    
    avg_days_overdue = sum(days_overdue_list) / len(days_overdue_list) if days_overdue_list else 0
    
    return {
        "status": "success",
        "report_date": today.strftime("%Y-%m-%d"),
        "kpis": {
            "invoice_metrics": {
                "total_invoices": total_invoices,
                "unpaid_invoices": total_unpaid,
                "paid_invoices": total_paid,
                "overdue_invoices": total_overdue,
                "overdue_rate_percentage": round(overdue_rate, 1),
            },
            "financial_metrics": {
                "total_revenue": round(total_revenue, 2),
                "total_outstanding": round(total_unpaid_amount, 2),
                "total_overdue_amount": round(total_overdue_amount, 2),
                "total_collected": round(total_paid_amount, 2),
                "collection_rate_percentage": round(collection_rate, 1),
                "average_invoice_amount": round(avg_invoice_amount, 2),
            },
            "customer_metrics": {
                "total_customers": len(partners),
                "customers_with_overdue": len(overdue_partners),
                "overdue_customer_rate_percentage": round(len(overdue_partners) / len(partners) * 100, 1) if partners else 0,
            },
            "collections_metrics": {
                "average_days_overdue": round(avg_days_overdue, 1),
                "at_risk_amount": round(total_overdue_amount, 2),
            }
        }
    }


# ---------------------------------------------------------------------------
# Tool 20 — Get Payment Summary
# ---------------------------------------------------------------------------

def get_payment_summary(
    partner_id: str = "",
    days_back: int = 30
) -> dict:
    """Get a summary of payment activity and trends.
    
    Provides insights into payment patterns over a specified time period.
    Can be filtered to a specific Business Partner or show all partners.
    
    Args:
        partner_id: Optional Business Partner ID to filter by. 
            Leave empty to see summary for all partners.
        days_back: Number of days to look back. Defaults to 30 days.
    
    Returns:
        Dict with payment summary including paid invoices, payment trends, and statistics.
    """
    # Calculate date range
    today = datetime.now()
    start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Build filter
    if partner_id:
        filter_expr = f"BusinessPartner eq '{partner_id}' and PaymentStatus eq 'Paid'"
    else:
        filter_expr = "PaymentStatus eq 'Paid'"
    
    # Get paid invoices
    result = read_records("Invoice", filter_expr)
    if result.get("error") or result.get("status") == "error":
        return result
    
    invoices = result.get("records", [])
    
    # Filter by date (manual filtering since OData filter is basic)
    recent_paid = []
    for inv in invoices:
        # Note: In a real system, we'd track payment date separately
        # For now, we'll include all paid invoices
        recent_paid.append(inv)
    
    # Calculate statistics
    total_paid = len(recent_paid)
    total_amount_paid = sum(inv.get("TotalNetAmount", 0) for inv in recent_paid)
    avg_payment_amount = total_amount_paid / total_paid if total_paid > 0 else 0
    
    # Get unpaid invoices for the partner
    if partner_id:
        unpaid_filter = f"BusinessPartner eq '{partner_id}' and PaymentStatus eq 'Unpaid'"
    else:
        unpaid_filter = "PaymentStatus eq 'Unpaid'"
    
    unpaid_result = read_records("Invoice", unpaid_filter)
    unpaid_invoices = unpaid_result.get("records", [])
    total_outstanding = sum(inv.get("TotalNetAmount", 0) for inv in unpaid_invoices)
    
    # Calculate payment success rate
    total_invoices = total_paid + len(unpaid_invoices)
    payment_success_rate = (total_paid / total_invoices * 100) if total_invoices > 0 else 0
    
    return {
        "status": "success",
        "report_date": today.strftime("%Y-%m-%d"),
        "period_days": days_back,
        "partner_id": partner_id if partner_id else "All Partners",
        "summary": {
            "invoices_paid": total_paid,
            "total_amount_paid": round(total_amount_paid, 2),
            "average_payment_amount": round(avg_payment_amount, 2),
            "invoices_outstanding": len(unpaid_invoices),
            "total_outstanding": round(total_outstanding, 2),
            "payment_success_rate_percentage": round(payment_success_rate, 1),
        },
        "recent_payments": [
            {
                "invoice_id": inv.get("BillingDocument"),
                "partner_id": inv.get("BusinessPartner"),
                "amount": inv.get("TotalNetAmount"),
                "currency": inv.get("TransactionCurrency"),
            }
            for inv in recent_paid[:10]  # Show top 10 recent
        ]
    }


# ---------------------------------------------------------------------------
# Tool 21 — Get Top Customers
# ---------------------------------------------------------------------------

def get_top_customers(
    criteria: str = "outstanding",
    limit: int = 10
) -> dict:
    """Get top customers based on various criteria.
    
    Useful for identifying high-value customers, risky accounts, or revenue drivers.
    
    Args:
        criteria: What to rank by. Options:
            'outstanding' - Highest unpaid amounts (default)
            'overdue' - Most overdue amount
            'revenue' - Highest total invoice amounts
            'invoice_count' - Most invoices
        limit: Maximum number of customers to return. Defaults to 10.
    
    Returns:
        Dict with top customers ranked by the specified criteria.
    """
    # Get all business partners
    partners_result = read_records("BusinessPartner", "")
    if partners_result.get("error"):
        return partners_result
    
    partners = partners_result.get("records", [])
    
    # Get all invoices
    invoices_result = read_records("Invoice", "")
    invoices = invoices_result.get("records", [])
    
    # Calculate metrics for each partner
    partner_metrics = {}
    
    for partner in partners:
        partner_id = partner.get("BusinessPartner")
        partner_name = partner.get("BusinessPartnerName")
        
        # Get partner's invoices
        partner_invoices = [inv for inv in invoices if inv.get("BusinessPartner") == partner_id]
        unpaid_invoices = [inv for inv in partner_invoices if inv.get("PaymentStatus") == "Unpaid"]
        overdue_invoices = [inv for inv in partner_invoices if inv.get("Status") == "Overdue"]
        
        outstanding_amount = sum(inv.get("TotalNetAmount", 0) for inv in unpaid_invoices)
        overdue_amount = sum(inv.get("TotalNetAmount", 0) for inv in overdue_invoices)
        total_revenue = sum(inv.get("TotalNetAmount", 0) for inv in partner_invoices)
        
        partner_metrics[partner_id] = {
            "partner_id": partner_id,
            "partner_name": partner_name,
            "outstanding_amount": outstanding_amount,
            "overdue_amount": overdue_amount,
            "total_revenue": total_revenue,
            "invoice_count": len(partner_invoices),
            "unpaid_count": len(unpaid_invoices),
            "overdue_count": len(overdue_invoices),
        }
    
    # Sort by criteria
    if criteria == "outstanding":
        sorted_partners = sorted(partner_metrics.values(), key=lambda x: x["outstanding_amount"], reverse=True)
        sort_key = "outstanding_amount"
    elif criteria == "overdue":
        sorted_partners = sorted(partner_metrics.values(), key=lambda x: x["overdue_amount"], reverse=True)
        sort_key = "overdue_amount"
    elif criteria == "revenue":
        sorted_partners = sorted(partner_metrics.values(), key=lambda x: x["total_revenue"], reverse=True)
        sort_key = "total_revenue"
    elif criteria == "invoice_count":
        sorted_partners = sorted(partner_metrics.values(), key=lambda x: x["invoice_count"], reverse=True)
        sort_key = "invoice_count"
    else:
        return {
            "status": "error",
            "message": f"Unknown criteria '{criteria}'. Use: 'outstanding', 'overdue', 'revenue', or 'invoice_count'"
        }
    
    # Get top N
    top_customers = sorted_partners[:limit]
    
    return {
        "status": "success",
        "criteria": criteria,
        "sort_key": sort_key,
        "limit": limit,
        "count": len(top_customers),
        "top_customers": top_customers
    }
