from . import dhl, ups, fedex, purolator, canada_post

_ALL = [dhl, ups, fedex, purolator, canada_post]


class CarrierError(Exception):
    pass


def active_carriers():
    return [c for c in _ALL if c.is_enabled()]
