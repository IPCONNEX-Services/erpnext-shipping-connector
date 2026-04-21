_CARRIER_NAME = "FedEx"


def is_enabled() -> bool:
    return False


def get_rates(origin: dict, destination: dict, packages: list) -> list:
    raise NotImplementedError("FedEx carrier not yet implemented")
