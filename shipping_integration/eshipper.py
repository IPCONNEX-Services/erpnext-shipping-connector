import frappe
import requests
from datetime import date

_CACHE_KEY = "eshipper_access_token"


class EShipperError(Exception):
    pass


def _get_settings():
    return frappe.get_single("Shipping Integration Settings")


def _get_token() -> str:
    cached = frappe.cache().get_value(_CACHE_KEY)
    if cached:
        return cached

    settings = _get_settings()
    try:
        resp = requests.post(
            f"{settings.eshipper_api_url}/api/v2/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.eshipper_client_id,
                "client_secret": settings.get_password("eshipper_client_secret"),
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise EShipperError(f"eShipper auth failed: {exc}") from exc

    expires_in = max(int(data.get("expires_in", 3600)) - 60, 60)
    frappe.cache().set_value(_CACHE_KEY, token, expires_in_sec=expires_in)
    return token


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    """
    Returns list of totalCharge floats from eShipper for one shipment.
    origin/destination: {street, city, province, postal_code, country}
    packages: [{weight_kg, width_cm, height_cm, depth_cm}]
    """
    if not packages:
        return []
    settings = _get_settings()
    token = _get_token()

    payload = {
        "scheduledShipDate": date.today().isoformat(),
        "pickupLocation": {
            "address": {
                "address1": origin.get("street", ""),
                "city": origin.get("city", ""),
                "province": origin.get("province", ""),
                "postalCode": origin.get("postal_code", ""),
                "country": origin.get("country", "CA"),
                "residential": False,
            }
        },
        "to": {
            "address": {
                "address1": destination.get("street", ""),
                "city": destination.get("city", ""),
                "province": destination.get("province", ""),
                "postalCode": destination.get("postal_code", ""),
                "country": destination.get("country", "CA"),
                "residential": True,
            }
        },
        "packages": [
            {
                "weight": p.get("weight_kg") or 1.0,
                "length": p.get("depth_cm") or 20,
                "width": p.get("width_cm") or 20,
                "height": p.get("height_cm") or 10,
                "type": "parcel",
            }
            for p in packages
        ],
        "currencyCode": "CAD",
    }

    try:
        resp = requests.post(
            f"{settings.eshipper_api_url}/api/v2/ship",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise EShipperError(f"eShipper rate fetch failed: {exc}") from exc

    rates = data.get("rates", [])
    return [
        float(r["totalCharge"]["amount"])
        for r in rates
        if r.get("totalCharge") and r["totalCharge"].get("amount") is not None
    ]
