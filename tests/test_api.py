import pytest
import json
from unittest.mock import patch, MagicMock

from shipping_integration import api
from shipping_integration.eshipper import EShipperError


def _make_settings(frappe_stub, supplier_map=None, api_key="secret_key"):
    settings = MagicMock()
    settings.get_password.return_value = api_key
    settings.default_origin_street = "100 IPCONNEX Blvd"
    settings.default_origin_city = "Edmonton"
    settings.default_origin_province = "AB"
    settings.default_origin_postal = "T5J 0N3"
    settings.default_origin_country = "CA"
    settings.get.return_value = supplier_map or []
    frappe_stub.get_single.return_value = settings
    return settings


def _make_request(frappe_stub, key="secret_key"):
    frappe_stub.request = MagicMock()
    frappe_stub.request.headers = {"X-Shipping-Key": key}


_ITEM = {"item_code": "ITEM1", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20}
_DEST = {"street": "456 Oak", "city": "Calgary", "province": "AB", "postal_code": "T2P 1J9", "country": "CA"}


# ── _group_by_origin tests ──────────────────────────────────────────────────

def test_group_by_origin_uses_default_when_no_supplier_match(frappe_stub):
    _make_settings(frappe_stub)
    frappe_stub.db.get_value.return_value = None

    settings = frappe_stub.get_single.return_value
    groups = api._group_by_origin([_ITEM], settings)

    assert len(groups) == 1
    assert groups[0]["origin"]["city"] == "Edmonton"


def test_group_by_origin_groups_same_supplier_together(frappe_stub):
    row = MagicMock()
    row.supplier = "Synnex"
    row.street = "500 Synnex Dr"
    row.city = "Mississauga"
    row.province = "ON"
    row.postal_code = "L5T 2N7"
    row.country = "CA"
    _make_settings(frappe_stub, supplier_map=[row])
    frappe_stub.db.get_value.return_value = "Synnex"

    items = [
        {"item_code": "A", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20},
        {"item_code": "B", "weight_kg": 2.0, "width_cm": 30, "height_cm": 15, "depth_cm": 25},
    ]
    groups = api._group_by_origin(items, frappe_stub.get_single.return_value)

    assert len(groups) == 1
    assert len(groups[0]["packages"]) == 2
    assert groups[0]["origin"]["city"] == "Mississauga"


def test_group_by_origin_splits_different_suppliers(frappe_stub):
    row = MagicMock()
    row.supplier = "Synnex"
    row.street = "500 Synnex Dr"
    row.city = "Mississauga"
    row.province = "ON"
    row.postal_code = "L5T 2N7"
    row.country = "CA"
    _make_settings(frappe_stub, supplier_map=[row])

    frappe_stub.db.get_value.side_effect = lambda dt, name, field: "Synnex" if name == "A" else None

    items = [
        {"item_code": "A", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20},
        {"item_code": "B", "weight_kg": 2.0, "width_cm": 30, "height_cm": 15, "depth_cm": 25},
    ]
    groups = api._group_by_origin(items, frappe_stub.get_single.return_value)

    assert len(groups) == 2


# ── get_rates endpoint tests ────────────────────────────────────────────────

def test_get_rates_averages_one_group(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    frappe_stub.db.get_value.return_value = None
    frappe_stub.db.get_value.side_effect = None

    with patch("shipping_integration.api.eshipper") as mock_eshipper:
        mock_eshipper.get_rates.return_value = [10.0, 20.0, 30.0]
        result = api.get_rates(items=[_ITEM], destination=_DEST)

    assert result["rate"] == 20.0  # average of [10, 20, 30]
    assert result["currency"] == "CAD"


def test_get_rates_sums_across_two_groups(frappe_stub):
    """Two groups each averaging to different rates → summed total."""
    row = MagicMock()
    row.supplier = "Synnex"
    row.street = "500 Synnex Dr"
    row.city = "Mississauga"
    row.province = "ON"
    row.postal_code = "L5T 2N7"
    row.country = "CA"
    _make_settings(frappe_stub, supplier_map=[row])
    _make_request(frappe_stub)

    frappe_stub.db.get_value.side_effect = lambda dt, name, field: "Synnex" if name == "A" else None

    items = [
        {"item_code": "A", "weight_kg": 1.0, "width_cm": 20, "height_cm": 10, "depth_cm": 20},
        {"item_code": "B", "weight_kg": 2.0, "width_cm": 30, "height_cm": 15, "depth_cm": 25},
    ]

    call_count = [0]
    def eshipper_get_rates(origin, dest, packages):
        call_count[0] += 1
        if origin["city"] == "Mississauga":
            return [10.0, 20.0]   # avg = 15.0
        return [30.0, 40.0]       # avg = 35.0

    with patch("shipping_integration.api.eshipper") as mock_eshipper:
        mock_eshipper.get_rates.side_effect = eshipper_get_rates
        mock_eshipper.EShipperError = EShipperError
        result = api.get_rates(items=items, destination=_DEST)

    assert call_count[0] == 2
    assert result["rate"] == 50.0  # 15.0 + 35.0
    assert result["currency"] == "CAD"


def test_get_rates_rejects_wrong_api_key(frappe_stub):
    _make_settings(frappe_stub, api_key="real_secret")
    frappe_stub.request = MagicMock()
    frappe_stub.request.headers = {"X-Shipping-Key": "wrong_key"}
    frappe_stub.AuthenticationError = Exception

    frappe_stub.throw.side_effect = frappe_stub.AuthenticationError

    with pytest.raises(Exception):
        api.get_rates(items=[_ITEM], destination=_DEST)


def test_get_rates_rejects_missing_api_key_config(frappe_stub):
    """If qtsi_api_key is not configured in Settings → endpoint refuses."""
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
    frappe_stub.db.get_value.return_value = None
    frappe_stub.db.get_value.side_effect = None

    with patch("shipping_integration.api.eshipper") as mock_eshipper:
        mock_eshipper.get_rates.return_value = [15.0]
        result = api.get_rates(
            items=json.dumps([_ITEM]),
            destination=json.dumps(_DEST),
        )

    assert result["rate"] == 15.0


def test_get_rates_propagates_eshipper_error(frappe_stub):
    _make_settings(frappe_stub)
    _make_request(frappe_stub)
    frappe_stub.db.get_value.return_value = None
    frappe_stub.db.get_value.side_effect = None
    frappe_stub.throw.side_effect = Exception("Could not reach shipping service")

    with patch("shipping_integration.api.eshipper") as mock_eshipper:
        mock_eshipper.get_rates.side_effect = EShipperError("timeout")
        mock_eshipper.EShipperError = EShipperError
        with pytest.raises(Exception, match="Could not reach"):
            api.get_rates(items=[_ITEM], destination=_DEST)

    frappe_stub.log_error.assert_called_once()
