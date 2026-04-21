# Carrier Plugin System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the shipping connector from a single eShipper-only integration into a multi-carrier plugin system that queries all active carriers in parallel and returns all rate options sorted cheapest-first.

**Architecture:** Each carrier lives in `shipping_integration/carriers/<name>.py` and exposes two functions: `is_enabled()` and `get_rates()`. A registry in `carriers/__init__.py` lists all known carriers and filters to active ones. `api.py` fans out to all active carriers in parallel via `ThreadPoolExecutor` and merges results into `{rates: [...], errors: [...]}`.

**Tech Stack:** Python 3.9+, Frappe/ERPNext, `concurrent.futures.ThreadPoolExecutor`, `requests`, `pytest`, `unittest.mock`

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `shipping_integration/carriers/__init__.py` | `CarrierError` exception, `active_carriers()` registry |
| Create | `shipping_integration/carriers/eshipper.py` | eShipper API client (moved from root) |
| Create | `shipping_integration/carriers/dhl.py` | DHL stub (always disabled) |
| Create | `shipping_integration/carriers/ups.py` | UPS stub (always disabled) |
| Create | `shipping_integration/carriers/fedex.py` | FedEx stub (always disabled) |
| Create | `shipping_integration/carriers/purolator.py` | Purolator stub (always disabled) |
| Create | `shipping_integration/carriers/canada_post.py` | Canada Post stub (always disabled) |
| Create | `shipping_integration/doctype/eshipper_settings/eshipper_settings.json` | eShipper credentials DocType |
| Create | `shipping_integration/doctype/eshipper_settings/eshipper_settings.py` | DocType class (empty) |
| Create | `shipping_integration/doctype/dhl_settings/dhl_settings.json` | DHL credentials DocType |
| Create | `shipping_integration/doctype/dhl_settings/dhl_settings.py` | DocType class (empty) |
| Create | `shipping_integration/doctype/ups_settings/ups_settings.json` | UPS credentials DocType |
| Create | `shipping_integration/doctype/ups_settings/ups_settings.py` | DocType class (empty) |
| Create | `shipping_integration/doctype/fedex_settings/fedex_settings.json` | FedEx credentials DocType |
| Create | `shipping_integration/doctype/fedex_settings/fedex_settings.py` | DocType class (empty) |
| Create | `shipping_integration/doctype/purolator_settings/purolator_settings.json` | Purolator credentials DocType |
| Create | `shipping_integration/doctype/purolator_settings/purolator_settings.py` | DocType class (empty) |
| Create | `shipping_integration/doctype/canada_post_settings/canada_post_settings.json` | Canada Post credentials DocType |
| Create | `shipping_integration/doctype/canada_post_settings/canada_post_settings.py` | DocType class (empty) |
| Create | `tests/test_carriers_registry.py` | Registry unit tests |
| Create | `tests/test_carriers_eshipper.py` | eShipper carrier unit tests (migrated from test_eshipper.py) |
| Modify | `shipping_integration/carriers/__init__.py` | Add eshipper import after Task 3 |
| Modify | `shipping_integration/doctype/shipping_integration_settings/shipping_integration_settings.json` | Remove eShipper credential fields |
| Modify | `shipping_integration/api.py` | Fan-out logic, new response format |
| Modify | `tests/conftest.py` | Inject frappe stub into carriers/eshipper module |
| Modify | `tests/test_api.py` | Update for new response format and fan-out |
| Delete | `shipping_integration/eshipper.py` | Replaced by carriers/eshipper.py |
| Delete | `tests/test_eshipper.py` | Replaced by tests/test_carriers_eshipper.py |

---

## Task 1: Scaffold `carriers/` package with registry and stub modules

**Files:**
- Create: `shipping_integration/carriers/__init__.py`
- Create: `shipping_integration/carriers/dhl.py`
- Create: `shipping_integration/carriers/ups.py`
- Create: `shipping_integration/carriers/fedex.py`
- Create: `shipping_integration/carriers/purolator.py`
- Create: `shipping_integration/carriers/canada_post.py`
- Create: `shipping_integration/doctype/dhl_settings/dhl_settings.json`
- Create: `shipping_integration/doctype/dhl_settings/dhl_settings.py`
- Create: `shipping_integration/doctype/ups_settings/ups_settings.json`
- Create: `shipping_integration/doctype/ups_settings/ups_settings.py`
- Create: `shipping_integration/doctype/fedex_settings/fedex_settings.json`
- Create: `shipping_integration/doctype/fedex_settings/fedex_settings.py`
- Create: `shipping_integration/doctype/purolator_settings/purolator_settings.json`
- Create: `shipping_integration/doctype/purolator_settings/purolator_settings.py`
- Create: `shipping_integration/doctype/canada_post_settings/canada_post_settings.json`
- Create: `shipping_integration/doctype/canada_post_settings/canada_post_settings.py`
- Create: `tests/test_carriers_registry.py`

- [ ] **Step 1: Write the failing registry tests**

Create `tests/test_carriers_registry.py`:

```python
import pytest
import sys
from unittest.mock import MagicMock

# Ensure frappe stub is in sys.modules before any import
_stub = MagicMock()
sys.modules.setdefault("frappe", _stub)

from shipping_integration.carriers import active_carriers, CarrierError


def test_active_carriers_returns_only_enabled(monkeypatch):
    from shipping_integration.carriers import _ALL
    enabled = MagicMock()
    enabled.is_enabled.return_value = True
    disabled = MagicMock()
    disabled.is_enabled.return_value = False
    monkeypatch.setattr("shipping_integration.carriers._ALL", [enabled, disabled])

    result = active_carriers()

    assert result == [enabled]


def test_active_carriers_empty_when_none_enabled(monkeypatch):
    disabled = MagicMock()
    disabled.is_enabled.return_value = False
    monkeypatch.setattr("shipping_integration.carriers._ALL", [disabled])

    assert active_carriers() == []


def test_carrier_error_is_exception():
    err = CarrierError("something failed")
    assert isinstance(err, Exception)
    assert str(err) == "something failed"


def test_stub_carriers_are_never_enabled():
    from shipping_integration.carriers import dhl, ups, fedex, purolator, canada_post
    for carrier in [dhl, ups, fedex, purolator, canada_post]:
        assert carrier.is_enabled() is False, f"{carrier.__name__} should be disabled"


def test_stub_carriers_raise_not_implemented():
    from shipping_integration.carriers import dhl
    with pytest.raises(NotImplementedError):
        dhl.get_rates({}, {}, [])
```

- [ ] **Step 2: Run tests — expect ImportError (module doesn't exist yet)**

```bash
cd /Users/omarelmohri/Claude/erpnext-shipping-connector
python3 -m pytest tests/test_carriers_registry.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'shipping_integration.carriers'`

- [ ] **Step 3: Create the carriers package**

Create `shipping_integration/carriers/__init__.py`:

```python
from . import dhl, ups, fedex, purolator, canada_post

_ALL = [dhl, ups, fedex, purolator, canada_post]


class CarrierError(Exception):
    pass


def active_carriers():
    return [c for c in _ALL if c.is_enabled()]
```

- [ ] **Step 4: Create stub carrier modules**

Create `shipping_integration/carriers/dhl.py`:

```python
_CARRIER_NAME = "DHL"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("DHL carrier not yet implemented")
```

Create `shipping_integration/carriers/ups.py`:

```python
_CARRIER_NAME = "UPS"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("UPS carrier not yet implemented")
```

Create `shipping_integration/carriers/fedex.py`:

```python
_CARRIER_NAME = "FedEx"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("FedEx carrier not yet implemented")
```

Create `shipping_integration/carriers/purolator.py`:

```python
_CARRIER_NAME = "Purolator"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("Purolator carrier not yet implemented")
```

Create `shipping_integration/carriers/canada_post.py`:

```python
_CARRIER_NAME = "Canada Post"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("Canada Post carrier not yet implemented")
```

- [ ] **Step 5: Create stub DocType JSONs**

Create `shipping_integration/doctype/dhl_settings/dhl_settings.json`:

```json
{
  "doctype": "DocType",
  "name": "DHL Settings",
  "module": "Shipping Integration",
  "issingle": 1,
  "fields": [
    {"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled", "default": "0"},
    {"fieldname": "api_key", "fieldtype": "Password", "label": "API Key"},
    {"fieldname": "account_number", "fieldtype": "Data", "label": "Account Number"}
  ],
  "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
}
```

Create `shipping_integration/doctype/dhl_settings/dhl_settings.py`:

```python
from frappe.model.document import Document

class DHLSettings(Document):
    pass
```

Create `shipping_integration/doctype/ups_settings/ups_settings.json`:

```json
{
  "doctype": "DocType",
  "name": "UPS Settings",
  "module": "Shipping Integration",
  "issingle": 1,
  "fields": [
    {"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled", "default": "0"},
    {"fieldname": "client_id", "fieldtype": "Data", "label": "Client ID"},
    {"fieldname": "client_secret", "fieldtype": "Password", "label": "Client Secret"},
    {"fieldname": "account_number", "fieldtype": "Data", "label": "Account Number"}
  ],
  "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
}
```

Create `shipping_integration/doctype/ups_settings/ups_settings.py`:

```python
from frappe.model.document import Document

class UPSSettings(Document):
    pass
```

Create `shipping_integration/doctype/fedex_settings/fedex_settings.json`:

```json
{
  "doctype": "DocType",
  "name": "FedEx Settings",
  "module": "Shipping Integration",
  "issingle": 1,
  "fields": [
    {"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled", "default": "0"},
    {"fieldname": "client_id", "fieldtype": "Data", "label": "Client ID"},
    {"fieldname": "client_secret", "fieldtype": "Password", "label": "Client Secret"},
    {"fieldname": "account_number", "fieldtype": "Data", "label": "Account Number"}
  ],
  "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
}
```

Create `shipping_integration/doctype/fedex_settings/fedex_settings.py`:

```python
from frappe.model.document import Document

class FedExSettings(Document):
    pass
```

Create `shipping_integration/doctype/purolator_settings/purolator_settings.json`:

```json
{
  "doctype": "DocType",
  "name": "Purolator Settings",
  "module": "Shipping Integration",
  "issingle": 1,
  "fields": [
    {"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled", "default": "0"},
    {"fieldname": "api_key", "fieldtype": "Password", "label": "API Key"},
    {"fieldname": "password", "fieldtype": "Password", "label": "Password"},
    {"fieldname": "account_number", "fieldtype": "Data", "label": "Account Number"}
  ],
  "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
}
```

Create `shipping_integration/doctype/purolator_settings/purolator_settings.py`:

```python
from frappe.model.document import Document

class PurolatorSettings(Document):
    pass
```

Create `shipping_integration/doctype/canada_post_settings/canada_post_settings.json`:

```json
{
  "doctype": "DocType",
  "name": "Canada Post Settings",
  "module": "Shipping Integration",
  "issingle": 1,
  "fields": [
    {"fieldname": "enabled", "fieldtype": "Check", "label": "Enabled", "default": "0"},
    {"fieldname": "username", "fieldtype": "Data", "label": "Username"},
    {"fieldname": "password", "fieldtype": "Password", "label": "Password"},
    {"fieldname": "customer_number", "fieldtype": "Data", "label": "Customer Number"}
  ],
  "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}]
}
```

Create `shipping_integration/doctype/canada_post_settings/canada_post_settings.py`:

```python
from frappe.model.document import Document

class CanadaPostSettings(Document):
    pass
```

- [ ] **Step 6: Run tests — expect all pass**

```bash
python3 -m pytest tests/test_carriers_registry.py -v
```

Expected: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add shipping_integration/carriers/ \
        shipping_integration/doctype/dhl_settings/ \
        shipping_integration/doctype/ups_settings/ \
        shipping_integration/doctype/fedex_settings/ \
        shipping_integration/doctype/purolator_settings/ \
        shipping_integration/doctype/canada_post_settings/ \
        tests/test_carriers_registry.py
git commit -m "feat: scaffold carriers package with registry, CarrierError, and stub modules"
```

---

## Task 2: Create eShipper Settings DocType

**Files:**
- Create: `shipping_integration/doctype/eshipper_settings/eshipper_settings.json`
- Create: `shipping_integration/doctype/eshipper_settings/eshipper_settings.py`

- [ ] **Step 1: Create the DocType JSON**

Create `shipping_integration/doctype/eshipper_settings/eshipper_settings.json`:

```json
{
  "doctype": "DocType",
  "name": "eShipper Settings",
  "module": "Shipping Integration",
  "issingle": 1,
  "fields": [
    {
      "fieldname": "enabled",
      "fieldtype": "Check",
      "label": "Enabled",
      "default": "0"
    },
    {
      "fieldname": "api_url",
      "fieldtype": "Data",
      "label": "API Base URL",
      "description": "e.g. https://api.eshipper.com"
    },
    {
      "fieldname": "client_id",
      "fieldtype": "Data",
      "label": "Client ID"
    },
    {
      "fieldname": "col_break_1",
      "fieldtype": "Column Break"
    },
    {
      "fieldname": "client_secret",
      "fieldtype": "Password",
      "label": "Client Secret"
    }
  ],
  "permissions": [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1}
  ]
}
```

- [ ] **Step 2: Create the DocType Python class**

Create `shipping_integration/doctype/eshipper_settings/eshipper_settings.py`:

```python
from frappe.model.document import Document

class eShipperSettings(Document):
    pass
```

- [ ] **Step 3: Commit**

```bash
git add shipping_integration/doctype/eshipper_settings/
git commit -m "feat: add eShipper Settings DocType"
```

---

## Task 3: Migrate eshipper to carriers/eshipper.py

**Files:**
- Create: `shipping_integration/carriers/eshipper.py`
- Modify: `shipping_integration/carriers/__init__.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_carriers_eshipper.py`

- [ ] **Step 1: Write the failing carrier tests**

Create `tests/test_carriers_eshipper.py`:

```python
import pytest
import requests as requests_lib
from unittest.mock import patch, MagicMock

from shipping_integration.carriers import eshipper, CarrierError


def _mock_settings(frappe_stub, enabled=True, api_url="https://api.eshipper.com",
                   client_id="test_id", client_secret="test_secret"):
    settings = MagicMock()
    settings.enabled = enabled
    settings.api_url = api_url
    settings.client_id = client_id
    settings.get_password.return_value = client_secret
    frappe_stub.get_single.return_value = settings
    frappe_stub.cache.return_value.get_value.return_value = None
    return settings


def test_is_enabled_true_when_all_fields_set(frappe_stub):
    _mock_settings(frappe_stub)
    assert eshipper.is_enabled() is True


def test_is_enabled_false_when_disabled(frappe_stub):
    _mock_settings(frappe_stub, enabled=False)
    assert eshipper.is_enabled() is False


def test_is_enabled_false_when_no_client_id(frappe_stub):
    _mock_settings(frappe_stub, client_id="")
    assert eshipper.is_enabled() is False


def test_is_enabled_false_when_no_client_secret(frappe_stub):
    _mock_settings(frappe_stub, client_secret="")
    assert eshipper.is_enabled() is False


def test_get_token_posts_to_oauth_endpoint(frappe_stub):
    _mock_settings(frappe_stub)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "tok123", "expires_in": 3600}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp) as mock_post:
        token = eshipper._get_token()

    assert token == "tok123"
    call_url = mock_post.call_args[0][0]
    assert "oauth" in call_url or "token" in call_url


def test_get_token_uses_cache(frappe_stub):
    _mock_settings(frappe_stub)
    frappe_stub.cache.return_value.get_value.return_value = "cached_token"

    with patch("requests.post") as mock_post:
        token = eshipper._get_token()

    assert token == "cached_token"
    mock_post.assert_not_called()


def test_get_rates_returns_list_of_dicts(frappe_stub):
    _mock_settings(frappe_stub)
    frappe_stub.cache.return_value.get_value.return_value = "tok"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "rates": [
            {"totalCharge": {"amount": "12.50"}},
            {"totalCharge": {"amount": "28.00"}},
        ]
    }

    origin = {"street": "123 Main", "city": "Edmonton", "province": "AB",
              "postal_code": "T5J 0N3", "country": "CA"}
    dest = {"street": "456 Oak", "city": "Calgary", "province": "AB",
            "postal_code": "T2P 1J9", "country": "CA"}
    packages = [{"weight_kg": 2.0, "width_cm": 30, "height_cm": 10, "depth_cm": 20}]

    with patch("requests.post", return_value=mock_resp):
        rates = eshipper.get_rates(origin, dest, packages)

    assert rates == [
        {"carrier": "eShipper", "rate": 12.50, "currency": "CAD"},
        {"carrier": "eShipper", "rate": 28.00, "currency": "CAD"},
    ]


def test_get_rates_empty_packages_returns_empty_list(frappe_stub):
    with patch("requests.post") as mock_post:
        rates = eshipper.get_rates({}, {}, [])
    assert rates == []
    mock_post.assert_not_called()


def test_get_rates_empty_response_returns_empty_list(frappe_stub):
    _mock_settings(frappe_stub)
    frappe_stub.cache.return_value.get_value.return_value = "tok"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"rates": []}
    with patch("requests.post", return_value=mock_resp):
        rates = eshipper.get_rates({"city": "Edmonton"}, {"city": "Calgary"}, [{"weight_kg": 1.0}])
    assert rates == []


def test_get_token_raises_carrier_error_on_connection_error(frappe_stub):
    _mock_settings(frappe_stub)
    with patch("requests.post", side_effect=requests_lib.ConnectionError("refused")):
        with pytest.raises(CarrierError, match="eShipper auth failed"):
            eshipper._get_token()


def test_get_token_raises_carrier_error_on_missing_access_token(frappe_stub):
    _mock_settings(frappe_stub)
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {}
    with patch("requests.post", return_value=mock_resp):
        with pytest.raises(CarrierError, match="eShipper auth failed"):
            eshipper._get_token()


def test_get_rates_raises_carrier_error_on_timeout(frappe_stub):
    _mock_settings(frappe_stub)
    frappe_stub.cache.return_value.get_value.return_value = "tok"
    with patch("requests.post", side_effect=requests_lib.Timeout("timed out")):
        with pytest.raises(CarrierError, match="eShipper rate fetch failed"):
            eshipper.get_rates({"city": "Edmonton"}, {"city": "Calgary"}, [{"weight_kg": 1.0}])
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
python3 -m pytest tests/test_carriers_eshipper.py -v 2>&1 | head -10
```

Expected: `ImportError: cannot import name 'eshipper' from 'shipping_integration.carriers'`

- [ ] **Step 3: Create carriers/eshipper.py**

Create `shipping_integration/carriers/eshipper.py`:

```python
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
```

- [ ] **Step 4: Add eshipper to the registry**

Edit `shipping_integration/carriers/__init__.py` — replace the entire file:

```python
from . import eshipper, dhl, ups, fedex, purolator, canada_post

_ALL = [eshipper, dhl, ups, fedex, purolator, canada_post]


class CarrierError(Exception):
    pass


def active_carriers():
    return [c for c in _ALL if c.is_enabled()]
```

- [ ] **Step 5: Update conftest.py to inject frappe into the new module**

Replace `tests/conftest.py`:

```python
import sys
import pytest
from unittest.mock import MagicMock


def _make_frappe_stub():
    stub = MagicMock()
    stub.cache.return_value.get_value.return_value = None

    def _passthrough_whitelist(*args, **kwargs):
        def decorator(fn):
            return fn
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator

    stub.whitelist.side_effect = _passthrough_whitelist
    return stub


_initial_stub = _make_frappe_stub()
sys.modules.setdefault("frappe", _initial_stub)


@pytest.fixture(autouse=True)
def frappe_stub():
    stub = _make_frappe_stub()
    sys.modules["frappe"] = stub
    import shipping_integration.api as _api_mod
    import shipping_integration.carriers.eshipper as _eshipper_mod
    _api_mod.frappe = stub
    _eshipper_mod.frappe = stub
    yield stub
    sys.modules.pop("frappe", None)
```

- [ ] **Step 6: Run the new carrier tests**

```bash
python3 -m pytest tests/test_carriers_eshipper.py tests/test_carriers_registry.py -v
```

Expected: all pass (11 + 5 = 16 tests)

- [ ] **Step 7: Commit**

```bash
git add shipping_integration/carriers/eshipper.py \
        shipping_integration/carriers/__init__.py \
        tests/conftest.py \
        tests/test_carriers_eshipper.py
git commit -m "feat: migrate eshipper module into carriers package, add eShipper Settings"
```

---

## Task 4: Remove eShipper credential fields from Shipping Integration Settings

**Files:**
- Modify: `shipping_integration/doctype/shipping_integration_settings/shipping_integration_settings.json`

The fields `eshipper_api_url`, `eshipper_client_id`, `col_break_1`, and `eshipper_client_secret` move to the new `eShipper Settings` DocType and must be removed from the old settings.

- [ ] **Step 1: Update the settings JSON**

Replace `shipping_integration/doctype/shipping_integration_settings/shipping_integration_settings.json` with:

```json
{
 "doctype": "DocType",
 "name": "Shipping Integration Settings",
 "module": "Shipping Integration",
 "issingle": 1,
 "fields": [
  {
   "fieldname": "eshipper_section",
   "fieldtype": "Section Break",
   "label": "Caller Authentication"
  },
  {
   "fieldname": "caller_api_key",
   "fieldtype": "Password",
   "label": "Caller API Key",
   "description": "Secret key sent by the calling system in the X-Shipping-Key header"
  },
  {
   "fieldname": "origin_section",
   "fieldtype": "Section Break",
   "label": "Default Origin (IPCONNEX Warehouse)"
  },
  {
   "fieldname": "default_origin_address",
   "fieldtype": "Link",
   "label": "Default Origin Address",
   "options": "Address",
   "reqd": 1,
   "description": "Select the ERPNext Address record for the default shipping origin"
  },
  {
   "fieldname": "suppliers_section",
   "fieldtype": "Section Break",
   "label": "Supplier Warehouse Mapping"
  },
  {
   "fieldname": "supplier_warehouse_map",
   "fieldtype": "Table",
   "label": "Supplier Warehouses",
   "options": "Supplier Warehouse Map"
  }
 ],
 "permissions": [
  {"role": "System Manager", "read": 1, "write": 1, "create": 1}
 ]
}
```

- [ ] **Step 2: Run the full test suite — all should still pass**

```bash
python3 -m pytest tests/ -v
```

Expected: all previously passing tests still pass (DocType JSON changes don't affect Python tests)

- [ ] **Step 3: Commit**

```bash
git add shipping_integration/doctype/shipping_integration_settings/shipping_integration_settings.json
git commit -m "refactor: remove eShipper credential fields from Shipping Integration Settings"
```

---

## Task 5: Rewrite api.py with fan-out and new response format

**Files:**
- Modify: `shipping_integration/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write the failing fan-out tests**

Replace `tests/test_api.py` with:

```python
import pytest
import json
from unittest.mock import patch, MagicMock

from shipping_integration import api
from shipping_integration.carriers import CarrierError


def _make_settings(frappe_stub, api_key="secret_key"):
    settings = MagicMock()
    settings.get_password.return_value = api_key
    settings.default_origin_address = "IPCONNEX-Main"
    settings.get.return_value = []
    frappe_stub.get_single.return_value = settings
    frappe_stub.get_doc.side_effect = _make_addr_doc_lookup()
    frappe_stub.db.get_value.side_effect = _db_side_effect()
    return settings


def _make_addr_doc(street="100 Default St", city="Edmonton", state="AB",
                   pincode="T5J 0N3", country="Canada"):
    addr = MagicMock()
    addr.address_line1 = street
    addr.city = city
    addr.state = state
    addr.pincode = pincode
    addr.country = country
    return addr


_DEFAULT_ADDR_NAME = "IPCONNEX-Main"
_DEFAULT_ADDR = _make_addr_doc()


def _make_addr_doc_lookup():
    def side_effect(doctype, name):
        return {_DEFAULT_ADDR_NAME: _DEFAULT_ADDR}.get(name, MagicMock())
    return side_effect


def _db_side_effect(item_supplier_map=None):
    item_supplier_map = item_supplier_map or {}
    def side_effect(doctype, name, field):
        if doctype == "Country":
            return "ca"
        if doctype == "Item":
            return item_supplier_map.get(name)
        return None
    return side_effect


def _make_request(frappe_stub, key="secret_key"):
    frappe_stub.request = MagicMock()
    frappe_stub.request.headers = {"X-Shipping-Key": key}


_ITEM = {"item_code": "ITEM1", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20}
_DEST = {"street": "456 Oak", "city": "Calgary", "province": "AB", "postal_code": "T2P 1J9", "country": "CA"}


def _make_fake_carrier(name, rates=None, error=None):
    """Create a fake carrier module for testing fan-out."""
    carrier = MagicMock()
    carrier._CARRIER_NAME = name
    carrier.is_enabled.return_value = True
    if error:
        carrier.get_rates.side_effect = error
    else:
        carrier.get_rates.return_value = rates or [
            {"carrier": name, "rate": 10.0, "currency": "CAD"}
        ]
    return carrier


# ── _group_by_origin tests (unchanged behaviour) ────────────────────────────

def test_group_by_origin_uses_default_when_no_supplier_match(frappe_stub):
    _make_settings(frappe_stub)
    settings = frappe_stub.get_single.return_value
    groups = api._group_by_origin([_ITEM], settings)
    assert len(groups) == 1
    assert groups[0]["origin"]["city"] == "Edmonton"


# ── fan-out tests ────────────────────────────────────────────────────────────

def test_fan_out_single_carrier_single_group(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    carrier = _make_fake_carrier("MockCarrier", rates=[
        {"carrier": "MockCarrier", "rate": 15.0, "currency": "CAD"},
        {"carrier": "MockCarrier", "rate": 25.0, "currency": "CAD"},
    ])

    with patch("shipping_integration.api.active_carriers", return_value=[carrier]):
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    # min rate for single group = 15.0
    assert result["rates"] == [{"carrier": "MockCarrier", "rate": 15.0, "currency": "CAD"}]
    assert result["errors"] == []


def test_fan_out_two_carriers_sorted_cheapest_first(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    cheap = _make_fake_carrier("Cheap", rates=[{"carrier": "Cheap", "rate": 8.0, "currency": "CAD"}])
    expensive = _make_fake_carrier("Expensive", rates=[{"carrier": "Expensive", "rate": 20.0, "currency": "CAD"}])

    with patch("shipping_integration.api.active_carriers", return_value=[expensive, cheap]):
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    assert result["rates"][0]["carrier"] == "Cheap"
    assert result["rates"][1]["carrier"] == "Expensive"
    assert result["errors"] == []


def test_fan_out_failed_carrier_goes_to_errors(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    good = _make_fake_carrier("GoodCarrier", rates=[{"carrier": "GoodCarrier", "rate": 12.0, "currency": "CAD"}])
    bad = _make_fake_carrier("BadCarrier", error=CarrierError("API down"))

    with patch("shipping_integration.api.active_carriers", return_value=[good, bad]):
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    assert len(result["rates"]) == 1
    assert result["rates"][0]["carrier"] == "GoodCarrier"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["carrier"] == "BadCarrier"


def test_fan_out_carrier_with_empty_rates_is_silently_dropped(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    good = _make_fake_carrier("GoodCarrier", rates=[{"carrier": "GoodCarrier", "rate": 12.0, "currency": "CAD"}])
    empty = _make_fake_carrier("EmptyCarrier", rates=[])

    with patch("shipping_integration.api.active_carriers", return_value=[good, empty]):
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    assert len(result["rates"]) == 1
    assert result["errors"] == []


def test_fan_out_all_carriers_fail_returns_empty_rates(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    bad1 = _make_fake_carrier("Bad1", error=CarrierError("down"))
    bad2 = _make_fake_carrier("Bad2", error=CarrierError("down"))

    with patch("shipping_integration.api.active_carriers", return_value=[bad1, bad2]):
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    assert result["rates"] == []
    assert len(result["errors"]) == 2


def test_fan_out_no_active_carriers_returns_empty(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)

    with patch("shipping_integration.api.active_carriers", return_value=[]):
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    assert result == {"rates": [], "errors": []}


def test_fan_out_multi_group_carrier_dropped_if_fails_one_group(frappe_stub):
    """Carrier that fails one origin group is excluded from rates entirely."""
    row = MagicMock()
    row.supplier = "Synnex"
    row.address = "Synnex-Addr"
    _make_settings(frappe_stub)
    frappe_stub.get_single.return_value.get.return_value = [row]

    synnex_addr = _make_addr_doc(street="500 Synnex Dr", city="Mississauga",
                                  state="ON", pincode="L5T 2N7")
    frappe_stub.get_doc.side_effect = lambda dt, name: {
        _DEFAULT_ADDR_NAME: _DEFAULT_ADDR,
        "Synnex-Addr": synnex_addr,
    }.get(name, MagicMock())
    frappe_stub.db.get_value.side_effect = _db_side_effect(item_supplier_map={"A": "Synnex"})
    _make_request(frappe_stub)

    items = [
        {"item_code": "A", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20},
        {"item_code": "B", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20},
    ]

    call_count = [0]
    def selective_fail(origin, dest, packages):
        call_count[0] += 1
        if origin["city"] == "Mississauga":
            raise CarrierError("Synnex origin unavailable")
        return [{"carrier": "PartialCarrier", "rate": 10.0, "currency": "CAD"}]

    partial_carrier = MagicMock()
    partial_carrier._CARRIER_NAME = "PartialCarrier"
    partial_carrier.is_enabled.return_value = True
    partial_carrier.get_rates.side_effect = selective_fail

    with patch("shipping_integration.api.active_carriers", return_value=[partial_carrier]):
        result = api.get_rates(items=items, destination=_DEST)

    assert result["rates"] == []
    assert result["errors"][0]["carrier"] == "PartialCarrier"


# ── auth + input validation tests ────────────────────────────────────────────

def test_get_rates_rejects_wrong_api_key(frappe_stub):
    _make_settings(frappe_stub, api_key="real_secret")
    frappe_stub.request = MagicMock()
    frappe_stub.request.headers = {"X-Shipping-Key": "wrong_key"}
    frappe_stub.AuthenticationError = Exception
    frappe_stub.throw.side_effect = frappe_stub.AuthenticationError

    with pytest.raises(Exception):
        api.get_rates(items=[_ITEM], destination=_DEST)


def test_get_rates_rejects_missing_api_key_config(frappe_stub):
    _make_settings(frappe_stub, api_key="")
    frappe_stub.AuthenticationError = Exception
    frappe_stub.throw.side_effect = frappe_stub.AuthenticationError

    with pytest.raises(Exception):
        api.get_rates(items=[_ITEM], destination=_DEST)


def test_get_rates_rejects_missing_items(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    frappe_stub.throw.side_effect = Exception("items and destination are required")

    with pytest.raises(Exception, match="items and destination"):
        api.get_rates(items=None, destination=_DEST)


def test_get_rates_parses_json_string_inputs(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    carrier = _make_fake_carrier("JSONCarrier", rates=[
        {"carrier": "JSONCarrier", "rate": 15.0, "currency": "CAD"}
    ])

    with patch("shipping_integration.api.active_carriers", return_value=[carrier]):
        result = api.get_rates(
            items=json.dumps([_ITEM]),
            destination=json.dumps(_DEST),
        )

    assert result["rates"][0]["rate"] == 15.0
```

- [ ] **Step 2: Run tests — expect failures on fan-out tests**

```bash
python3 -m pytest tests/test_api.py -v 2>&1 | tail -20
```

Expected: auth and grouping tests pass; fan-out tests fail with errors about old response format.

- [ ] **Step 3: Rewrite api.py**

Replace `shipping_integration/api.py` with:

```python
import hmac
import json
import frappe
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from shipping_integration.carriers import active_carriers, CarrierError


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
            carrier_name = getattr(carrier, "_CARRIER_NAME", carrier.__name__)
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
```

- [ ] **Step 4: Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass. `test_eshipper.py` may fail — that's fine, it gets deleted next task.

- [ ] **Step 5: Commit**

```bash
git add shipping_integration/api.py tests/test_api.py
git commit -m "feat: rewrite api.py with multi-carrier fan-out and new response format"
```

---

## Task 6: Delete old files and final verification

**Files:**
- Delete: `shipping_integration/eshipper.py`
- Delete: `tests/test_eshipper.py`

- [ ] **Step 1: Delete the old root eshipper module**

```bash
cd /Users/omarelmohri/Claude/erpnext-shipping-connector
git rm shipping_integration/eshipper.py
git rm tests/test_eshipper.py
```

- [ ] **Step 2: Run the full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected output includes all passing tests and nothing referencing the deleted files:
```
tests/test_api.py ............... PASSED
tests/test_carriers_eshipper.py ........... PASSED
tests/test_carriers_registry.py ..... PASSED
```

All tests should be green. If any test imports from `shipping_integration.eshipper` (the deleted root module), fix the import to `shipping_integration.carriers.eshipper`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove legacy eshipper.py and test_eshipper.py — replaced by carriers package"
```

- [ ] **Step 4: Run full suite one final time and confirm green**

```bash
python3 -m pytest tests/ -v --tb=short
```

Expected: zero failures, zero errors.
