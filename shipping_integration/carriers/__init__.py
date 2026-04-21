class CarrierError(Exception):
    pass


from . import eshipper, dhl, ups, fedex, purolator, canada_post  # noqa: E402

_ALL = [eshipper, dhl, ups, fedex, purolator, canada_post]


def active_carriers():
    return [c for c in _ALL if c.is_enabled()]
