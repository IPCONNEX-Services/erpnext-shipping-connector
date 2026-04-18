import hmac
import json
import frappe
from shipping_integration import eshipper


@frappe.whitelist(allow_guest=True)
def get_rates(items=None, destination=None):
    """
    POST /api/method/shipping_integration.api.get_rates
    Headers: X-Shipping-Key: <key>
    Body: {items: [...], destination: {...}}
    Returns: {rate: float, currency: "CAD"}
    """
    settings = frappe.get_single("Shipping Integration Settings")

    expected_key = settings.get_password("qtsi_api_key") or ""
    if not expected_key:
        frappe.throw("Shipping endpoint is not configured", frappe.AuthenticationError)
    provided_key = frappe.request.headers.get("X-Shipping-Key", "")
    if not hmac.compare_digest(provided_key, expected_key):
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    if not items or not destination:
        frappe.throw("items and destination are required")

    try:
        if isinstance(items, str):
            items = json.loads(items)
        if isinstance(destination, str):
            destination = json.loads(destination)
    except (json.JSONDecodeError, ValueError):
        frappe.throw("Invalid JSON in items or destination")

    groups = _group_by_origin(items, settings)

    total_rate = 0.0
    for group in groups:
        try:
            rates = eshipper.get_rates(group["origin"], destination, group["packages"])
            if rates:
                total_rate += sum(rates) / len(rates)
            else:
                frappe.log_error(
                    f"No rates returned for origin {group['origin'].get('city')}",
                    "Shipping Integration",
                )
        except eshipper.EShipperError as exc:
            frappe.log_error(str(exc), "Shipping Integration eShipper Error")
            frappe.throw(f"Could not reach shipping service: {exc}")
        except Exception as exc:
            frappe.log_error(str(exc), "Shipping Integration Unexpected Error")
            frappe.throw("An unexpected error occurred while fetching shipping rates")

    return {"rate": round(total_rate, 2), "currency": "CAD"}


def _group_by_origin(items: list, settings) -> list:
    """
    Returns [{origin: dict, packages: list}] — one entry per unique origin.
    Items with no supplier match fall back to the IPCONNEX default warehouse.
    """
    supplier_map = {
        row.supplier: {
            "street": row.street,
            "city": row.city,
            "province": row.province,
            "postal_code": row.postal_code,
            "country": row.country or "CA",
        }
        for row in (settings.get("supplier_warehouse_map") or [])
    }

    default_origin = {
        "street": settings.default_origin_street,
        "city": settings.default_origin_city,
        "province": settings.default_origin_province,
        "postal_code": settings.default_origin_postal,
        "country": settings.default_origin_country or "CA",
    }

    by_key: dict = {}
    for item in items:
        supplier = frappe.db.get_value("Item", item.get("item_code"), "preferred_supplier") or ""
        origin = supplier_map.get(supplier, default_origin)
        key = f"{origin['street']}|{origin['postal_code']}"

        if key not in by_key:
            by_key[key] = {"origin": origin, "packages": []}

        by_key[key]["packages"].append({
            "weight_kg": item.get("weight_kg") or 1.0,
            "width_cm": item.get("width_cm") or 20,
            "height_cm": item.get("height_cm") or 10,
            "depth_cm": item.get("depth_cm") or 20,
        })

    return list(by_key.values())
