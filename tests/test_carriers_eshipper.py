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
