# Carrier Plugin System — Design Spec

**Date:** 2026-04-21
**Status:** Approved
**Scope:** Rate fetching only (label generation out of scope)

---

## Problem

The shipping connector is eShipper-only. Adding DHL, UPS, FedEx, Purolator, and Canada Post as one-offs would create tangled, unmaintainable code. A plugin architecture lets each carrier live in isolation and be added without touching existing code.

---

## Goals

- Each carrier is an independent module with a standard interface
- All active carriers are queried in parallel per request
- Response returns all carrier options so the caller can choose
- A carrier that fails does not block results from other carriers
- Each carrier has its own credentials + enabled toggle in ERPNext

---

## Architecture

### File Layout

```
shipping_integration/
  carriers/
    __init__.py        ← registry
    eshipper.py        ← moved + refactored from root
    dhl.py             ← stub (always disabled until implemented)
    ups.py             ← stub
    fedex.py           ← stub
    purolator.py       ← stub
    canada_post.py     ← stub
  api.py               ← updated fan-out logic
  eshipper.py          ← deleted (replaced by carriers/eshipper.py)
  doctype/
    shipping_integration_settings/   ← unchanged
    eshipper_settings/               ← new
    dhl_settings/                    ← new
    ups_settings/                    ← new
    fedex_settings/                  ← new
    purolator_settings/              ← new
    canada_post_settings/            ← new
```

### Registry (`carriers/__init__.py`)

Explicit list — no auto-discovery magic:

```python
from . import eshipper, dhl, ups, fedex, purolator, canada_post

_ALL = [eshipper, dhl, ups, fedex, purolator, canada_post]

def active_carriers():
    return [c for c in _ALL if c.is_enabled()]
```

---

## Carrier Module Interface

Every carrier module exposes exactly two functions:

```python
def is_enabled() -> bool:
    """Return True if enabled=1 and required credentials are set."""

def get_rates(origin: dict, destination: dict, packages: list) -> list[dict]:
    """
    origin / destination: {street, city, province, postal_code, country}
    packages: [{weight_kg, width_cm, height_cm, depth_cm}]
    Returns: [{"carrier": "<Name>", "rate": <float>, "currency": "CAD"}, ...]
    Raises: CarrierError on any failure.
    """
```

`is_enabled()` checks both the `enabled` boolean field AND that required credential fields are non-empty. Enabling a carrier with missing credentials is a no-op.

Stub carriers (not yet implemented) have `is_enabled()` always return `False` and `get_rates()` raise `NotImplementedError`.

A shared `CarrierError` exception class lives in `carriers/__init__.py`. Each carrier raises it on API failures.

---

## Settings (DocTypes)

`Shipping Integration Settings` is unchanged — it keeps the caller API key, default origin address, and supplier warehouse map.

Each carrier gets its own **Single DocType** with an `enabled` checkbox and carrier-specific credential fields:

| DocType | Fields |
|---|---|
| eShipper Settings | enabled, api_url, client_id, client_secret¹ |
| DHL Settings | enabled, api_key¹, account_number |
| UPS Settings | enabled, client_id, client_secret¹, account_number |
| FedEx Settings | enabled, client_id, client_secret¹, account_number |
| Purolator Settings | enabled, api_key¹, password¹, account_number |
| Canada Post Settings | enabled, username, password¹, customer_number |

¹ Password fieldtype (encrypted at rest)

All carrier Settings DocTypes are System Manager only (read + write).

---

## API Fan-out

`api.py` is updated as follows:

1. Resolve origin groups from items (unchanged)
2. Get `active_carriers()` from registry
3. For each carrier × origin group: submit `get_rates()` to a `ThreadPoolExecutor`
4. Collect futures with a 15-second timeout per carrier
5. Aggregate: for each carrier, sum its lowest rate across all origin groups
6. A carrier must quote every origin group to appear in results — partial group coverage drops the carrier entirely
7. Return merged response

---

## Response Format

**Breaking change** from `{rate, currency}` to:

```json
{
  "rates": [
    {"carrier": "eShipper", "rate": 21.50, "currency": "CAD"},
    {"carrier": "Purolator", "rate": 18.00, "currency": "CAD"}
  ],
  "errors": [
    {"carrier": "DHL", "error": "timeout"}
  ]
}
```

- `rates` is sorted cheapest-first
- `errors` lists carriers that were active but failed
- Both arrays are always present (empty if nothing to report)
- HTTP 200 even when `rates` is empty — caller interprets the payload

Existing callers that read `response.rate` must be updated to read `response.rates[0].rate` (cheapest).

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Carrier timeout (>15s) | Logged to Frappe error log; added to `errors[]` |
| Carrier raises `CarrierError` | Logged; added to `errors[]` |
| Carrier returns empty rates for a group | Carrier dropped silently (no error entry) |
| Carrier fails one of multiple origin groups | Carrier dropped entirely from `rates[]` |
| All carriers fail | `{rates: [], errors: [...]}` — HTTP 200 |
| Zero active carriers | `{rates: [], errors: []}` — no fan-out |

---

## Testing

- Each carrier module tested in isolation: mock `requests`, assert correct payload shape sent to carrier API, assert `get_rates()` return format.
- `api.py` tested with mocked `active_carriers()` — no real network calls.
- One test verifies parallel fan-out + error merging: two fake carrier modules (one succeeds, one raises), assert correct `rates` and `errors` in response.
- `is_enabled()` tested with mocked Single DocType values.
- Existing `test_eshipper.py` tests migrated to `tests/test_carriers_eshipper.py`.

---

## Out of Scope

- Label generation (future spec)
- Package tracking (future spec)
- Carrier rate caching
- Carrier-specific surcharge breakdown
