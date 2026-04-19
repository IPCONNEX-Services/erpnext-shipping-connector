# ERPNext Shipping Connector

## Purpose
Integrates eShipper API with ERPNext for multi-carrier shipping rate calculation
and shipment creation. Fetches live rates from eShipper, aggregates by origin
warehouse, and presents them on ERPNext shipment documents.
Published on the Frappe Cloud marketplace. Version: 0.0.1.

## Paid Tier
FREE — all features included at no cost.

## Tech Stack
- Frappe v15+ / ERPNext v15+
- Python 3.10+
- eShipper REST API (OAuth2 client credentials)
- pytest for tests

## Key Files
- `shipping_integration/hooks.py` — app metadata, fixtures registration
- `shipping_integration/doctype/` — DocTypes: Shipping Settings, Shipment, rate models
- `shipping_integration/api/` — eShipper API client, rate aggregation, OAuth2 token management
- `shipping_integration/utils/` — shared helpers
- `docs/` — API reference, configuration guide, integration guides
- `tests/` — pytest suite (test_api.py, test_eshipper.py, conftest.py)

## Common Tasks

### Add a new carrier
1. Add carrier-specific rate parser in `shipping_integration/api/`
2. Register it in the rate aggregation logic
3. Add a test in `tests/test_eshipper.py` using the existing mock pattern from `conftest.py`
4. Update `docs/api.md` with the new carrier's fields

### Add a DocType field
1. Edit the DocType JSON in `shipping_integration/doctype/<name>/<name>.json`
2. Write a patch if existing installs need migration
3. Register patch in `shipping_integration/patches.txt`

### Update OAuth2 token refresh logic
- Token management lives in `shipping_integration/api/` — look for the OAuth2 client module
- eShipper tokens expire; the refresh must be automatic and thread-safe

### Run the test suite
```bash
cd /Users/omarelmohri/Claude/erpnext-shipping-connector
pytest tests/ -v
```

### Cut a release
1. Bump `__version__` in `shipping_integration/__init__.py` (this is the version source for setup.py)
2. Follow Release Procedure in the Frappe/ERPNext skill.

## Gotchas
- eShipper OAuth2 tokens expire — always check token validity before API calls; do not cache tokens longer than their `expires_in` value
- Rate aggregation is by origin warehouse — if a warehouse is missing or misconfigured, rates silently return empty
- `setup.py` reads version from `shipping_integration/__init__.py` — bump version there, not in setup.py
- Fixtures export the full DocType module — be careful when adding fields that existing installs already have (write a patch)

## Secrets
eShipper API credentials (client ID + secret) — to be provided for testing. Store in Frappe site config or a Settings DocType, never hardcoded.
