"""
Mock SAP S/4HANA OData Server
=============================
Simulates real SAP OData endpoints with in-memory data storage.
Provides CRUD operations for Business Partners, Invoices, Sales Orders, and Materials.
Includes a web dashboard UI for browsing created records.
"""

import uuid
import threading
from datetime import datetime, date

from flask import Flask, request, jsonify, render_template


# ---------------------------------------------------------------------------
# In-memory data store (thread-safe access via lock)
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_data = {
    "BusinessPartners": {},
    "Invoices": {},
    "SalesOrders": {},
    "Materials": {},
}

_bp_counter = 0  # For SAP-style BP IDs like BP0000000001


def _next_bp_id():
    global _bp_counter
    _bp_counter += 1
    return f"BP{_bp_counter:010d}"


def _next_id(prefix=""):
    short = uuid.uuid4().hex[:8].upper()
    return f"{prefix}{short}" if prefix else short


def _now_iso():
    return datetime.utcnow().isoformat() + "Z"


def _compute_invoice_status(inv: dict) -> str:
    """Derive status from due date and payment info."""
    if inv.get("PaymentStatus") == "Paid":
        return "Paid"
    if inv.get("DueDate"):
        try:
            due = date.fromisoformat(inv["DueDate"])
            if due < date.today():
                return "Overdue"
        except (ValueError, TypeError):
            pass
    return "Open"


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)


# ---- Dashboard UI ---------------------------------------------------------
@app.route("/")
def dashboard():
    with _lock:
        stats = {k: len(v) for k, v in _data.items()}
        return render_template(
            "dashboard.html",
            stats=stats,
            partners=list(_data["BusinessPartners"].values()),
            invoices=list(_data["Invoices"].values()),
            sales_orders=list(_data["SalesOrders"].values()),
            materials=list(_data["Materials"].values()),
        )


# ---- Health ---------------------------------------------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ===========================================================================
#  API_BUSINESS_PARTNER  —  /sap/opu/odata/sap/API_BUSINESS_PARTNER/
# ===========================================================================
BP_BASE = "/sap/opu/odata/sap/API_BUSINESS_PARTNER"


@app.route(f"{BP_BASE}/A_BusinessPartner", methods=["GET"])
def list_partners():
    with _lock:
        results = list(_data["BusinessPartners"].values())
    results = _apply_filter(results, request.args.get("$filter"))
    return jsonify({"d": {"results": results}})


@app.route(f"{BP_BASE}/A_BusinessPartner", methods=["POST"])
def create_partner():
    body = request.get_json(force=True)
    bp_id = _next_bp_id()
    partner = {
        "BusinessPartner": bp_id,
        "BusinessPartnerName": body.get("BusinessPartnerName", ""),
        "BusinessPartnerCategory": body.get("BusinessPartnerCategory", "1"),
        "BusinessPartnerType": body.get("BusinessPartnerType", "Customer"),
        "Country": body.get("Country", ""),
        "City": body.get("City", ""),
        "StreetName": body.get("StreetName", ""),
        "PostalCode": body.get("PostalCode", ""),
        "Region": body.get("Region", ""),
        "CreditLimit": body.get("CreditLimit", 0.0),
        "Currency": body.get("Currency", "USD"),
        "CreatedAt": _now_iso(),
    }
    with _lock:
        _data["BusinessPartners"][bp_id] = partner
    return jsonify({"d": partner}), 201


@app.route(f"{BP_BASE}/A_BusinessPartner('<bp_id>')", methods=["GET"])
def get_partner(bp_id):
    with _lock:
        partner = _data["BusinessPartners"].get(bp_id)
    if not partner:
        return jsonify({"error": {"message": f"Business Partner '{bp_id}' not found"}}), 404
    return jsonify({"d": partner})


@app.route(f"{BP_BASE}/A_BusinessPartner('<bp_id>')", methods=["PATCH", "PUT"])
def update_partner(bp_id):
    with _lock:
        partner = _data["BusinessPartners"].get(bp_id)
        if not partner:
            return jsonify({"error": {"message": f"Business Partner '{bp_id}' not found"}}), 404
        body = request.get_json(force=True)
        for key, val in body.items():
            if key in partner:
                partner[key] = val
        _data["BusinessPartners"][bp_id] = partner
    return jsonify({"d": partner})


# ===========================================================================
#  API_BILLING_DOCUMENT  —  /sap/opu/odata/sap/API_BILLING_DOCUMENT/
# ===========================================================================
INV_BASE = "/sap/opu/odata/sap/API_BILLING_DOCUMENT"


@app.route(f"{INV_BASE}/A_BillingDocument", methods=["GET"])
def list_invoices():
    with _lock:
        results = list(_data["Invoices"].values())
        # Recompute statuses on read
        for inv in results:
            inv["Status"] = _compute_invoice_status(inv)
    results = _apply_filter(results, request.args.get("$filter"))
    return jsonify({"d": {"results": results}})


@app.route(f"{INV_BASE}/A_BillingDocument", methods=["POST"])
def create_invoice():
    body = request.get_json(force=True)
    inv_id = _next_id("INV")
    invoice = {
        "BillingDocument": inv_id,
        "BusinessPartner": body.get("BusinessPartner", ""),
        "TotalNetAmount": body.get("TotalNetAmount", 0.0),
        "TransactionCurrency": body.get("TransactionCurrency", "USD"),
        "BillingDocumentDate": body.get("BillingDocumentDate", date.today().isoformat()),
        "DueDate": body.get("DueDate", ""),
        "PaymentStatus": body.get("PaymentStatus", "Unpaid"),
        "LineItems": body.get("LineItems", []),
        "CreatedAt": _now_iso(),
    }
    invoice["Status"] = _compute_invoice_status(invoice)
    with _lock:
        _data["Invoices"][inv_id] = invoice
    return jsonify({"d": invoice}), 201


@app.route(f"{INV_BASE}/A_BillingDocument('<inv_id>')", methods=["GET"])
def get_invoice(inv_id):
    with _lock:
        invoice = _data["Invoices"].get(inv_id)
    if not invoice:
        return jsonify({"error": {"message": f"Invoice '{inv_id}' not found"}}), 404
    invoice["Status"] = _compute_invoice_status(invoice)
    return jsonify({"d": invoice})


@app.route(f"{INV_BASE}/A_BillingDocument('<inv_id>')", methods=["PATCH", "PUT"])
def update_invoice(inv_id):
    with _lock:
        invoice = _data["Invoices"].get(inv_id)
        if not invoice:
            return jsonify({"error": {"message": f"Invoice '{inv_id}' not found"}}), 404
        body = request.get_json(force=True)
        for key, val in body.items():
            if key in invoice:
                invoice[key] = val
        invoice["Status"] = _compute_invoice_status(invoice)
        _data["Invoices"][inv_id] = invoice
    return jsonify({"d": invoice})


# ===========================================================================
#  API_SALES_ORDER_SRV  —  /sap/opu/odata/sap/API_SALES_ORDER_SRV/
# ===========================================================================
SO_BASE = "/sap/opu/odata/sap/API_SALES_ORDER_SRV"


@app.route(f"{SO_BASE}/A_SalesOrder", methods=["GET"])
def list_sales_orders():
    with _lock:
        results = list(_data["SalesOrders"].values())
    results = _apply_filter(results, request.args.get("$filter"))
    return jsonify({"d": {"results": results}})


@app.route(f"{SO_BASE}/A_SalesOrder", methods=["POST"])
def create_sales_order():
    body = request.get_json(force=True)
    so_id = _next_id("SO")
    order = {
        "SalesOrder": so_id,
        "BusinessPartner": body.get("BusinessPartner", ""),
        "SalesOrderType": body.get("SalesOrderType", "OR"),
        "SalesOrganization": body.get("SalesOrganization", "1000"),
        "RequestedDeliveryDate": body.get("RequestedDeliveryDate", ""),
        "TotalNetAmount": body.get("TotalNetAmount", 0.0),
        "TransactionCurrency": body.get("TransactionCurrency", "USD"),
        "OverallStatus": body.get("OverallStatus", "Open"),
        "LineItems": body.get("LineItems", []),
        "CreatedAt": _now_iso(),
    }
    with _lock:
        _data["SalesOrders"][so_id] = order
    return jsonify({"d": order}), 201


@app.route(f"{SO_BASE}/A_SalesOrder('<so_id>')", methods=["GET"])
def get_sales_order(so_id):
    with _lock:
        order = _data["SalesOrders"].get(so_id)
    if not order:
        return jsonify({"error": {"message": f"Sales Order '{so_id}' not found"}}), 404
    return jsonify({"d": order})


@app.route(f"{SO_BASE}/A_SalesOrder('<so_id>')", methods=["PATCH", "PUT"])
def update_sales_order(so_id):
    with _lock:
        order = _data["SalesOrders"].get(so_id)
        if not order:
            return jsonify({"error": {"message": f"Sales Order '{so_id}' not found"}}), 404
        body = request.get_json(force=True)
        for key, val in body.items():
            if key in order:
                order[key] = val
        _data["SalesOrders"][so_id] = order
    return jsonify({"d": order})


# ===========================================================================
#  API_PRODUCT_SRV  —  /sap/opu/odata/sap/API_PRODUCT_SRV/
# ===========================================================================
MAT_BASE = "/sap/opu/odata/sap/API_PRODUCT_SRV"


@app.route(f"{MAT_BASE}/A_Product", methods=["GET"])
def list_materials():
    with _lock:
        results = list(_data["Materials"].values())
    results = _apply_filter(results, request.args.get("$filter"))
    return jsonify({"d": {"results": results}})


@app.route(f"{MAT_BASE}/A_Product", methods=["POST"])
def create_material():
    body = request.get_json(force=True)
    mat_id = _next_id("MAT")
    material = {
        "Product": mat_id,
        "ProductName": body.get("ProductName", ""),
        "ProductType": body.get("ProductType", "FERT"),
        "BaseUnit": body.get("BaseUnit", "EA"),
        "StandardPrice": body.get("StandardPrice", 0.0),
        "Currency": body.get("Currency", "USD"),
        "ProductGroup": body.get("ProductGroup", ""),
        "CreatedAt": _now_iso(),
    }
    with _lock:
        _data["Materials"][mat_id] = material
    return jsonify({"d": material}), 201


@app.route(f"{MAT_BASE}/A_Product('<mat_id>')", methods=["GET"])
def get_material(mat_id):
    with _lock:
        material = _data["Materials"].get(mat_id)
    if not material:
        return jsonify({"error": {"message": f"Product '{mat_id}' not found"}}), 404
    return jsonify({"d": material})


@app.route(f"{MAT_BASE}/A_Product('<mat_id>')", methods=["PATCH", "PUT"])
def update_material(mat_id):
    with _lock:
        material = _data["Materials"].get(mat_id)
        if not material:
            return jsonify({"error": {"message": f"Product '{mat_id}' not found"}}), 404
        body = request.get_json(force=True)
        for key, val in body.items():
            if key in material:
                material[key] = val
        _data["Materials"][mat_id] = material
    return jsonify({"d": material})


# ===========================================================================
#  Reset endpoint (for testing)
# ===========================================================================
@app.route("/admin/reset", methods=["POST"])
def reset_data():
    global _bp_counter
    with _lock:
        for key in _data:
            _data[key].clear()
        _bp_counter = 0
    return jsonify({"message": "All data reset"})


# ===========================================================================
#  Simple OData $filter parser
# ===========================================================================
def _apply_filter(records: list, filter_str: str | None) -> list:
    """Very basic OData $filter support: field eq 'value' / field eq number."""
    if not filter_str:
        return records

    # Support multiple conditions joined by 'and'
    conditions = [c.strip() for c in filter_str.split(" and ")]
    filtered = records
    for cond in conditions:
        parts = cond.split(" eq ")
        if len(parts) != 2:
            continue
        field = parts[0].strip()
        value = parts[1].strip().strip("'")
        # Try numeric comparison
        try:
            num_val = float(value)
            filtered = [r for r in filtered if float(r.get(field, 0)) == num_val]
        except ValueError:
            filtered = [r for r in filtered if str(r.get(field, "")) == value]
    return filtered


# ===========================================================================
#  Standalone run
# ===========================================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
