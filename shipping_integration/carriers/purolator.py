_CARRIER_NAME = "Purolator"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("Purolator carrier not yet implemented")
