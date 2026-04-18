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


# Module-level stub so shipping_integration.api / eshipper can be imported
# at collection time before any fixture fires.
_initial_stub = _make_frappe_stub()
sys.modules.setdefault("frappe", _initial_stub)


@pytest.fixture(autouse=True)
def frappe_stub():
    stub = _make_frappe_stub()
    sys.modules["frappe"] = stub
    import shipping_integration.api as _api_mod
    import shipping_integration.eshipper as _eshipper_mod
    _api_mod.frappe = stub
    _eshipper_mod.frappe = stub
    yield stub
    sys.modules.pop("frappe", None)
