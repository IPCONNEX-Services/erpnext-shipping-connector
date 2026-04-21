import frappe
import requests
from datetime import date
from shipping_integration.carriers import CarrierError

_CACHE_KEY = "eshipper_access_token"
_CARRIER_NAME = "eShipper"


def is_enabled() -> bool:
    s = frappe.get_single("eShipper Settings")
    return bool(s.enabled and s.api_url and s.client_id and s.get_password("client_secret"))


def _get_settings():
    return frappe.get_single("eShipper Settings")


def _get_token() -> str:
    cached = frappe.cache().get_value(_CACHE_KEY)
    if cached:
        return cached

    settings = _get_settings()
    try:
        resp = requests.post(
            f"{settings.api_url}/api/v2/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": settings.client_id,
                "client_secret": settings.get_password("client_secret"),
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise CarrierError(f"eShipper auth failed: {exc}") from exc

    expires_in = max(int(data.get("expires_in", 3600)) - 60, 60)
    frappe.cache().set_value(_CACHE_KEY, token, expires_in_sec=expires_in)
    return token


def get_rates(origin: dict, destination: dict, packages: list) -> list:
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
            f"{settings.api_url}/api/v2/ship",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, KeyError, ValueError) as exc:
        raise CarrierError(f"eShipper rate fetch failed: {exc}") from exc

    raw_rates = data.get("rates", [])
    return [
        {"carrier": _CARRIER_NAME, "rate": float(r["totalCharge"]["amount"]), "currency": "CAD"}
        for r in raw_rates
        if r.get("totalCharge") and r["totalCharge"].get("amount") is not None
    ]
