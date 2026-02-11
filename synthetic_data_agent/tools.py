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

MOCK_SAP_URL = os.getenv("MOCK_SAP_URL", "http://localhost:8080")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _url(path: str) -> str:
    return f"{MOCK_SAP_URL}{path}"


def _post(path: str, data: dict) -> dict:
    resp = requests.post(_url(path), json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _patch(path: str, data: dict) -> dict:
    resp = requests.patch(_url(path), json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _get(path: str, params: dict | None = None) -> dict:
    resp = requests.get(_url(path), params=params or {}, timeout=10)
    resp.raise_for_status()
    return resp.json()


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
    records = result.get("d", {}).get("results", [])
    return {
        "entity_type": entity_type,
        "filter": filter_expression or "(none)",
        "count": len(records),
        "records": records,
    }
