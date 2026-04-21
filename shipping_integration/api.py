import hmac
import json
import frappe
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from shipping_integration.carriers import active_carriers
from shipping_integration.carriers.errors import CarrierError


@frappe.whitelist(allow_guest=True)
def get_rates(items=None, destination=None):
    """
    POST /api/method/shipping_integration.api.get_rates
    Headers: X-Shipping-Key: <key>
    Body: {items: [...], destination: {...}}
    Returns: {rates: [{carrier, rate, currency}, ...], errors: [{carrier, error}, ...]}
    """
    settings = frappe.get_single("Shipping Integration Settings")

    expected_key = settings.get_password("caller_api_key") or ""
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
    carriers = active_carriers()

    if not carriers:
        return {"rates": [], "errors": []}

    return _fan_out(carriers, groups, destination)


def _fan_out(carriers, groups, destination):
    errors = []
    carrier_totals = {}

    with ThreadPoolExecutor(max_workers=max(len(carriers) * len(groups), 1)) as executor:
        carrier_futures = {
            c: [
                executor.submit(c.get_rates, g["origin"], destination, g["packages"])
                for g in groups
            ]
            for c in carriers
        }

        for carrier, group_futures in carrier_futures.items():
            carrier_name = getattr(carrier, "_CARRIER_NAME", None) or getattr(carrier, "__name__", "unknown")
            total = 0.0
            failed = False

            for fut in group_futures:
                try:
                    rates = fut.result(timeout=15)
                    if not rates:
                        failed = True
                        break
                    total += min(r["rate"] for r in rates)
                except FuturesTimeoutError:
                    frappe.log_error(f"{carrier_name} timed out", "Shipping Integration")
                    errors.append({"carrier": carrier_name, "error": "timeout"})
                    failed = True
                    break
                except CarrierError as exc:
                    frappe.log_error(str(exc), f"Shipping Integration {carrier_name}")
                    errors.append({"carrier": carrier_name, "error": str(exc)})
                    failed = True
                    break
                except Exception as exc:
                    frappe.log_error(str(exc), f"Shipping Integration {carrier_name}")
                    errors.append({"carrier": carrier_name, "error": "unexpected error"})
                    failed = True
                    break

            if not failed:
                carrier_totals[carrier_name] = round(total, 2)

    rates = sorted(
        [{"carrier": name, "rate": rate, "currency": "CAD"} for name, rate in carrier_totals.items()],
        key=lambda r: r["rate"],
    )
    return {"rates": rates, "errors": errors}


def _resolve_address(address_name: str) -> dict:
    addr = frappe.get_doc("Address", address_name)
    country_code = (frappe.db.get_value("Country", addr.country, "code") or "ca").upper()
    return {
        "street": addr.address_line1,
        "city": addr.city,
        "province": addr.state,
        "postal_code": addr.pincode,
        "country": country_code,
    }


def _group_by_origin(items: list, settings) -> list:
    supplier_map = {
        row.supplier: row.address
        for row in (settings.get("supplier_warehouse_map") or [])
    }

    default_address_name = settings.default_origin_address
    default_origin = _resolve_address(default_address_name)

    by_key: dict = {}
    for item in items:
        supplier = frappe.db.get_value("Item", item.get("item_code"), "preferred_supplier") or ""
        address_name = supplier_map.get(supplier)
        origin = _resolve_address(address_name) if address_name else default_origin
        key = address_name or default_address_name

        if key not in by_key:
            by_key[key] = {"origin": origin, "packages": []}

        by_key[key]["packages"].append({
            "weight_kg": item.get("weight_kg") or 1.0,
            "width_cm": item.get("width_cm") or 20,
            "height_cm": item.get("height_cm") or 10,
            "depth_cm": item.get("depth_cm") or 20,
        })

    return list(by_key.values())
