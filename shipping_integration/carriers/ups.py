_CARRIER_NAME = "UPS"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("UPS carrier not yet implemented")
