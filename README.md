# erpnext-shipping-connector

[![ERPNext](https://img.shields.io/badge/ERPNext-v15-blue)](https://erpnext.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A standalone Frappe/ERPNext app that calculates live shipping costs via **eShipper**. Any authorized system sends items and a delivery address; the app groups shipments by supplier warehouse, fetches rates from eShipper, and returns a single aggregated CAD total.

---

## Features

- **Live eShipper rates** — queries the eShipper v2 API for real-time carrier quotes
- **Multi-origin grouping** — routes items from different supplier warehouses as separate shipments, then sums the costs
- **OAuth2 token caching** — eShipper access tokens are cached in Frappe's Redis cache (auto-refreshed on expiry)
- **HMAC-safe authentication** — callers authenticate with a pre-shared API key verified via constant-time comparison
- **Audit logging** — all eShipper errors are written to Frappe's Error Log for visibility

---

## Requirements

| Dependency | Version |
|---|---|
| Frappe | v15+ |
| ERPNext | v15+ |
| Python | 3.10+ |
| eShipper account | API v2 access |

---

## Installation

```bash
# On the target bench
bench get-app shipping_integration https://github.com/IPCONNEX-Services/erpnext-shipping-connector

bench --site <your-site> install-app shipping_integration
```

After installation, the **Shipping Integration Settings** DocType will be available in your ERPNext instance.

---

## Configuration

Navigate to **Shipping Integration Settings** in ERPNext and fill in the following sections.

### 1. eShipper API Credentials

| Field | Description |
|---|---|
| eShipper API URL | Base URL of the eShipper API (e.g. `https://api.eshipper.com`) |
| eShipper Client ID | OAuth2 client ID from your eShipper account |
| eShipper Client Secret | OAuth2 client secret (stored encrypted) |

> Get these from the eShipper portal under **Account → API Access**.

### 2. QTSI API Key

| Field | Description |
|---|---|
| QTSI API Key | Secret key sent by the calling system in the `X-Shipping-Key` header |

Generate a strong random string (e.g. `openssl rand -hex 32`) and share it with the calling system.

### 3. Default Origin Warehouse

The fallback shipping origin when an item's supplier has no mapped warehouse.

| Field | Required |
|---|---|
| Street | Yes |
| City | Yes |
| Province | Yes |
| Postal Code | Yes |
| Country | No (defaults to `CA`) |

### 4. Supplier Warehouse Map *(optional)*

Add one row per supplier that ships from a different location than the default warehouse. When an item's **Preferred Supplier** matches a row, that warehouse address is used as the pickup origin.

| Column | Description |
|---|---|
| Supplier | Link to Supplier DocType |
| Street | Warehouse street address |
| City | City |
| Province | Province / state code |
| Postal Code | Postal code |
| Country | Defaults to `CA` |

See [docs/configuration.md](docs/configuration.md) for a detailed field reference.

---

## API Reference

See [docs/api.md](docs/api.md) for the full reference with curl examples.

**Quick summary:**

```
POST /api/method/shipping_integration.api.get_rates
X-Shipping-Key: <your-qtsi-api-key>
Content-Type: application/json

{
  "items": [
    { "item_code": "ITEM-001", "qty": 2, "weight_kg": 1.5, "width_cm": 20, "height_cm": 10, "depth_cm": 20 }
  ],
  "destination": {
    "street": "123 Main St",
    "city": "Toronto",
    "province": "ON",
    "postal_code": "M5H 2N2",
    "country": "CA"
  }
}
```

**Response:**
```json
{ "message": { "rate": 24.50, "currency": "CAD" } }
```

---

## Rate Calculation Logic

```
For each item:
  1. Look up item's Preferred Supplier
  2. Map supplier → warehouse address (fallback: default IPCONNEX warehouse)

Group items by origin address (street + postal code)

For each group:
  - Request all carrier rates from eShipper
  - Average the returned rates

Total = sum of averaged rates across all groups
```

**Example:**

| Item | Supplier | Origin |
|---|---|---|
| Router | SupplierA | Warehouse A (Montreal) |
| Cable | SupplierA | Warehouse A (Montreal) |
| Server | SupplierB | Warehouse B (Toronto) |

→ Group 1 (Montreal): avg eShipper rates for Router + Cable  
→ Group 2 (Toronto): avg eShipper rates for Server  
→ **Total = Group 1 avg + Group 2 avg**

---

## Architecture

```
Caller (e.g. QTSI Store)
        │
        │  POST /api/method/shipping_integration.api.get_rates
        │  X-Shipping-Key: <key>
        ▼
┌─────────────────────────────────────┐
│         api.py                      │
│  1. Validate X-Shipping-Key (HMAC)  │
│  2. Parse items + destination       │
│  3. Group items by origin           │
└────────────────┬────────────────────┘
                 │  per origin group
                 ▼
┌─────────────────────────────────────┐
│         eshipper.py                 │
│  1. Get OAuth2 token (cached)       │
│  2. POST /api/v2/ship               │
│  3. Extract totalCharge amounts     │
└────────────────┬────────────────────┘
                 │
                 ▼
          eShipper API v2
                 │
                 ▼
┌─────────────────────────────────────┐
│         api.py (aggregation)        │
│  avg per group → sum all groups     │
│  return { rate, currency: "CAD" }   │
└─────────────────────────────────────┘
```

---

## Development & Testing

```bash
cd erpnext-shipping-connector
pip install pytest
pytest tests/ -v
```

Tests mock the `frappe` module and `requests` library — no running ERPNext instance required.

---

## License

MIT — see [LICENSE](LICENSE)
