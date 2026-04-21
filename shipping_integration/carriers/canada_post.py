_CARRIER_NAME = "Canada Post"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("Canada Post carrier not yet implemented")
