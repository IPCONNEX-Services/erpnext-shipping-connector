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
