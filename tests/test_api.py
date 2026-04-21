import pytest
import json
from unittest.mock import patch, MagicMock

from shipping_integration import api
from shipping_integration.carriers.errors import CarrierError


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


_SENTINEL = object()


def _make_fake_carrier(name, rates=_SENTINEL, error=None):
    """Create a fake carrier module for testing fan-out."""
    carrier = MagicMock()
    carrier._CARRIER_NAME = name
    carrier.is_enabled.return_value = True
    if error:
        carrier.get_rates.side_effect = error
    else:
        if rates is _SENTINEL:
            carrier.get_rates.return_value = [{"carrier": name, "rate": 10.0, "currency": "CAD"}]
        else:
            carrier.get_rates.return_value = rates
    return carrier


# ── _group_by_origin tests ────────────────────────────────────────────────────

def test_group_by_origin_uses_default_when_no_supplier_match(frappe_stub):
    _make_settings(frappe_stub)
    settings = frappe_stub.get_single.return_value
    groups = api._group_by_origin([_ITEM], settings)
    assert len(groups) == 1
    assert groups[0]["origin"]["city"] == "Edmonton"


# ── fan-out tests ─────────────────────────────────────────────────────────────

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
