_CARRIER_NAME = "DHL"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("DHL carrier not yet implemented")
